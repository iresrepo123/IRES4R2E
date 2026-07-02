import io.shiftleft.semanticcpg.language._
import io.shiftleft.codepropertygraph.generated.nodes.Method
import java.io.{File, PrintWriter}
import scala.io.Source
import java.util.regex.Pattern

case class InputItem(repo: String, path: String, func_name: String, raw_code: String)

case class SubContext(
    name: String,
    signature: String
)

case class ContextOutput(
    target_func: String,
    file_path: String,
    method_signature: String,
    method_body_no_sig: String,
    local_variables: List[String],
    class_name: String,
    class_fields: List[String],
    sibling_methods: List[String],
    callees: List[SubContext],
    callers: List[SubContext]
)


def unescapeJson(s: String): String = {
  if (s == null) return ""
  s.replace("\\n", "\n")
   .replace("\\t", "\t")
   .replace("\\\"", "\"")
   .replace("\\\\", "\\")
}

def extractBodyFromRaw(rawCodeEncoded: String): String = {
  val rawCode = unescapeJson(rawCodeEncoded)
  val start = rawCode.indexOf("{")
  val end = rawCode.lastIndexOf("}")
  
  if (start != -1 && end != -1 && end > start) {
    rawCode.substring(start + 1, end).trim
  } else {
    "" 
  }
}

def escape(s: String): String = {
  if (s == null) return ""
  s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
}

def subContextListToJson(list: List[SubContext]): String = {
  list.map { item =>
    s"""
    |    {
    |      "name": "${escape(item.name)}",
    |      "signature": "${escape(item.signature)}"
    |    }""".stripMargin
  }.mkString(", ")
}

def toJson(results: List[ContextOutput]): String = {
  val sb = new StringBuilder()
  sb.append("[\n")
  val size = results.size
  results.zipWithIndex.foreach { case (r, idx) =>
    sb.append("  {\n")
    sb.append(s"""    "target_func": "${escape(r.target_func)}",\n""")
    sb.append(s"""    "file_path": "${escape(r.file_path)}",\n""")
    sb.append(s"""    "method_signature": "${escape(r.method_signature)}",\n""")
    sb.append(s"""    "method_body_no_sig": "${escape(r.method_body_no_sig)}",\n""")
    sb.append(s"""    "local_variables": [${r.local_variables.map(v => "\"" + escape(v) + "\"").mkString(", ")}],\n""")
    sb.append(s"""    "class_name": "${escape(r.class_name)}",\n""")
    sb.append(s"""    "class_fields": [${r.class_fields.map(f => "\"" + escape(f) + "\"").mkString(", ")}],\n""")
    sb.append(s"""    "sibling_methods": [${r.sibling_methods.map(s => "\"" + escape(s) + "\"").mkString(", ")}],\n""")
    sb.append(s"""    "callees": [${subContextListToJson(r.callees)}],\n""")
    sb.append(s"""    "callers": [${subContextListToJson(r.callers)}]\n""")
    sb.append("  }")
    if (idx < size - 1) sb.append(",\n") else sb.append("\n")
  }
  sb.append("]")
  sb.toString()
}

def parseInput(jsonContent: String): List[InputItem] = {
  val items = scala.collection.mutable.ListBuffer[InputItem]()
  val content = jsonContent.trim.stripPrefix("[").stripSuffix("]")
  
  if (content.isEmpty) return List()

  val rawObjs = content.split("\\},")

  val repoRegex = """"repo"\s*:\s*"(.*?)"""".r
  val pathRegex = """"path"\s*:\s*"(.*?)"""".r
  val funcRegex = """"func_name"\s*:\s*"(.*?)"""".r
  
  val codeRegex = """"code"\s*:\s*"((?:[^"\\\\]|\\\\.)*)"""".r

  for (raw <- rawObjs) {
    val rawObj = if (raw.trim.endsWith("}")) raw else raw + "}"
    
    val repo = repoRegex.findFirstMatchIn(rawObj).map(_.group(1)).getOrElse("")
    val path = pathRegex.findFirstMatchIn(rawObj).map(_.group(1)).getOrElse("")
    val func = funcRegex.findFirstMatchIn(rawObj).map(_.group(1)).getOrElse("")
    val code = codeRegex.findFirstMatchIn(rawObj).map(_.group(1)).getOrElse("")
    
    if (repo.nonEmpty && func.nonEmpty) {
      items += InputItem(repo, path, func, code)
    }
  }
  items.toList
}


@main def exec() = {
    val projectPath = "./flink" 
    val inputJsonPath = "./apache_flink_sub.json"
    val outputJsonPath = "./flink_final_context_sub.json"

    println(s"[*] Generating CPG from source: $projectPath")
    importCode(projectPath)

    println(s"[*] Reading input list & RAW CODE from: $inputJsonPath")
    val jsonContent = Source.fromFile(inputJsonPath).getLines.mkString("\n")
    
    val inputList = parseInput(jsonContent)
    
    println(s"[*] Total targets to process: ${inputList.size}")

    val results = inputList.zipWithIndex.flatMap { case (item, idx) =>
        if ((idx + 1) % 50 == 0) println(s"    Processing item ${idx + 1}/${inputList.size}...")

        val rawMethodName = item.func_name.split("\\.").lastOption.getOrElse(item.func_name)

        val methods = cpg.file
            .name(".*" + java.util.regex.Pattern.quote(item.path))
            .method
            .nameExact(rawMethodName)
            .l

        methods.headOption match {
            case Some(m) =>
                try {
                    val signature = m.signature
                    
                    val bodyCleaned = extractBodyFromRaw(item.raw_code)

                    val locals = m.local.name.filterNot(_.startsWith("$")).filterNot(_ == "this").l
                    val typeDecl = m.typeDecl.headOption
                    val className = typeDecl.map(_.name).getOrElse("<unknown>")
                    val fields = typeDecl.map(_.member.filterNot(_.name.startsWith("<")).filterNot(_.name.contains("(")).name.l).getOrElse(List())
                    val siblings = typeDecl.map(_.method.filterNot(_.name == m.name).filterNot(_.name.startsWith("<")).signature.l).getOrElse(List())

                    val callees = m.call.callee
                        .filterNot(_.isExternal)
                        .filterNot(_.name.startsWith("<"))
                        .dedup.take(5)
                        .map { c => SubContext(c.name, c.signature) }.l

                    val callers = m.caller
                        .filterNot(_.name.startsWith("<"))
                        .dedup.take(5)
                        .map { c => SubContext(c.name, c.signature) }.l

                    Some(ContextOutput(
                        target_func = item.func_name,
                        file_path = m.filename,
                        method_signature = signature,
                        method_body_no_sig = bodyCleaned,
                        local_variables = locals,
                        class_name = className,
                        class_fields = fields,
                        sibling_methods = siblings,
                        callees = callees,
                        callers = callers
                    ))
                } catch {
                    case e: Exception =>
                        println(s"[!] Error processing ${item.func_name}: ${e.getMessage}")
                        None
                }
            case None => None
        }
    }

    println(s"[*] Writing ${results.size} results to $outputJsonPath")
    val jsonOutput = toJson(results)
    val writer = new PrintWriter(new File(outputJsonPath))
    writer.write(jsonOutput)
    writer.close()
    println("[*] Done.")
}

exec()