## Common Prompt

You are an expert technical writer specializing in Java documentation. Your task is to generate a summary for the provided Java method. Your task is to produce a clear, concise, and accurate summary of the provided Java method based on the user input, capturing its purpose, behavior, and key characteristics.

USER INPUT FORMAT SPECIFICATION:
The user input is structured using XML-style tags to prevent ambiguity:

- <task_scenario>: Specifies the summary's scope, constraints, and required focus.
- <input_data>: Contains the source material, organized into two distinct categories:
    1. **Target**: The raw source code of a single Java method to be summarized, explicitly marked as [Target Method].
    2. **Context**: Auxiliary information (e.g., [Class Context], [Call Graph Context]) for the method provided SOLELY to support the comprehension of this method.

**Important**: You must strictly adhere to  the constraints defined in the <task_scenario> tag.

PROCESS:
Step1: Carefully examine ALL content within <input_data> to fully understand the [Target method]'s purpose, behavior, and key characteristics.
Step2: Formulate a concise summary (under 30 words) that captures the primary Intent of the [Target Method].

CONSTRAINT:
- Do NOT hallucinate variables or logic not present in the <input_data>.
- Focus the summary on the [Target Method], not the **Context** itself.

OUTPUT FORMAT:
Output the summary as a single valid JSON object with the key "summary".
Example:
{
  "summary": "Your concise summary here."
}


## L1 Prompt

<task_scenario>

Analyze the provided [Target Method] signature. Infer the method's primary intent strictly based on its name, naming convention, return type, and parameter list.

</task_scenario>

<input_data>

[Target Method]

Method Signature: 

{signature}

</input_data>

Generate the JSON summary based on the Method Signature of the [Target Method].


## L2 Prompt

<task_scenario>

The complete source code of the [Target Method] is provided, including its method signature and method body. Analyze this code to determine its primary intent. Focus on core functionality and disregard auxiliary code like logging or assertions.

</task_scenario>

<input_data>

[Target Method]

Method Signature:

{signature}

Method Body:

{body}

</input_data>

Generate the JSON summary based on the Method Signature and Method Body of the [Target Method].


## L3 Prompt

<task_scenario>

The complete source code of the [Target Method] is provided, including its method signature and method body. Additionally, you have access to the enclosing Class Context information, including the Class Name (i.e., the name of the class that contains the [Target Method]), the File Path (i.e., the filesystem path of the java source file defining the class), the Field List (i.e., a comma-separated list of all  fields declared in the class), and the Sibling Methods (i.e., a comma-separated list of all other methods defined in the same class (excluding the [Target Method]). Use this contextual information to understand the role of the [Target Method] within this class. Critically, the summary must focus on the core functionality of the  [Target Method], not the general purpose of the class.

</task_scenario>

<input_data>
[Target Method]
Method Signature: 
{signature}

Method Body:
{body}

[Class Context]

- Class Name: {class_name}
- File Path: {file_path}
- Field List: {field_list}
- Sibling Methods: {sibling_methods}

</input_data>

Generate the JSON summary based on the Method Signature and Method Body of the [Target Method], and the Class Context information.


## L4 Prompt

<task_scenario>

The complete source code of the [Target Method] is provided, including its method signature and method body. Additionally, you have access to the [Call Graph Context], which lists the Called Methods (Callees) — i.e., methods that are directly invoked by the [Target Method]. The Called Methods are structured as a list of comma-separated callees. Analyze the `signature` and `file_path` of each Called Method (each callee) to deduce their specific functionality. Use this insight to infer the [Target Method]'s role within the overall call graph.

</task_scenario>

<input_data>
[Target Method]

Method Signature: 

{signature}

Method Body:

{body}

[Call Graph Context]

\- Called Methods (i.e., Callees): 

{callees}

</input_data>

Generate the JSON summary based on the Method Signature and Method Body of the [Target Method], and the Called Methods of [Target Method]'s [Call Graph Context].


## L5 Prompt

<task_scenario>

The complete source code of the [Target Method] is provided, including its method signature and method body. Additionally, you have access to the [Call Graph Context], which lists the Calling Methods (Callers) — i.e., methods that invoke the [Target Method]. The Calling Methods are structured as a list of comma-separated Callers. Analyze the `signature` and `file_path` of each Calling Method (each caller) to identify its specific usage scenarios. Use this insight to determine the [Target Method]'s service role or business intent within the broader system.

</task_scenario>

<input_data>

[Target Method]

Method Signature: 

{signature}

Method Body:

{body}

[Call Graph Context]

\- Calling Methods (Callers): 

{callers}

</input_data>

Generate the JSON summary based on the Method Signature and Method Body of the [Target Method], and the Calling Methods of [Target Method]'s [Call Graph Context].


## L6 Prompt

<task_scenario>

The complete source code of the [Target Method] is provided, including its method signature and method body. Additionally, you have access to the enclosing Class Context information, including the Class Name (i.e., the name of the class that contains the [Target Method]), the File Path (i.e., the filesystem path of the java source file defining the class), the Field List (i.e., a comma-separated list of all  fields declared in the class), and the Sibling Methods (i.e., a comma-separated list of all other methods defined in the same class (excluding the [Target Method]). Use this contextual information to understand the role of the [Target Method] within this class. Furthermore, you have access to the [Call Graph Context], which lists the Called Methods (Callees) — i.e., methods that are directly invoked by the [Target Method]. The Called Methods are structured as a list of comma-separated callees. Analyze the `signature` and `file_path` of each Called Method (each callee) to deduce their specific functionality. Use this insight to infer the [Target Method]'s role within the overall call graph. Synthesize the above information  to explain what the method does and how it fits into the class's responsibility.

</task_scenario>

<input_data>
[Target Method]
Method Signature: 
{signature}

Method Body:
{body}

[Class Context]

- Class Name: {class_name}
- File Path: {file_path}
- Field List: {field_list}
- Sibling Methods: {sibling_methods}

[Call Graph Context]
- Called Methods (Callees): 
{callees}


</input_data>

Generate the JSON summary based on the Method Signature and Method Body of the [Target Method], the [Class Context], and the Called Methods of [Target Method]'s [Call Graph Context].


## L7 Prompt



<task_scenario>

The complete source code of the [Target Method] is provided, including its method signature and method body. Additionally, you have access to the enclosing Class Context information, including the Class Name (i.e., the name of the class that contains the [Target Method]), the File Path (i.e., the filesystem path of the java source file defining the class), the Field List (i.e., a comma-separated list of all  fields declared in the class), and the Sibling Methods (i.e., a comma-separated list of all other methods defined in the same class (excluding the [Target Method]). Use this contextual information to understand the role of the [Target Method] within this class. Furthermore, you have access to the [Call Graph Context], which lists the Calling Methods (Callers) — i.e., methods that invoke the [Target Method]. The Calling Methods are structured as a list of comma-separated Callers. Analyze the `signature` and `file_path` of each Calling Method (each caller) to identify its specific usage scenarios. Use this insight to determine the [Target Method]'s service role or business intent within the broader system. Synthesize the above information  to explain what the method does and how it fits into the class's responsibility.

</task_scenario>

<input_data>
[Target Method]
Method Signature: 
{signature}

Method Body:
{body}

[Class Context]

- Class Name: {class_name}
- File Path: {file_path}
- Field List: {field_list}
- Sibling Methods: {sibling_methods}

[Call Graph Context]
- Calling Methods (Callers): 
{callers}

</input_data>

Generate the JSON summary based on the Method Signature and Method Body of the [Target Method], the [Class Context], and the Calling Methods of [Target Method]'s [Call Graph Context].


## L8 Prompt

<task_scenario>

The complete source code of the [Target Method] is provided, including its method signature and method body. Additionally, you have access to the [Call Graph Context], which lists the Called Methods (Callees) — i.e., methods that are directly invoked by the [Target Method], and the Calling Methods (Callers) — i.e., methods that invoke the [Target Method]. The Called Methods and Calling Methods are structured as a list of comma-separated callees and callers, respectively. Analyze the `signature` and `file_path` of each Called Method (or Calling Method) to deduce their specific functionality. Use this insight to infer the [Target Method]'s role within the overall call graph. Synthesize the above information to provide a complete view of the method's functionality.

</task_scenario>

<input_data>
[Target Method]
Method Signature: 
{signature}

Method Body:
{body}

[Call Graph Context]
- Called Methods (Callees): 
{callees}
- Calling Methods (Callers): 
{callers}

</input_data>

Generate the JSON summary based on the Method Signature and Method Body of the [Target Method], and the Called Methods and the Calling Methods of [Target Method]'s [Call Graph Context].


## L9 Prompt

<task_scenario>

The complete source code of the [Target Method] is provided, including its method signature and method body. Additionally, you have access to the enclosing Class Context information, including the Class Name (i.e., the name of the class that contains the [Target Method]), the File Path (i.e., the filesystem path of the java source file defining the class), the Field List (i.e., a comma-separated list of all  fields declared in the class), and the Sibling Methods (i.e., a comma-separated list of all other methods defined in the same class (excluding the [Target Method]). Use this contextual information to understand the role of the [Target Method] within this class. Furthermore, you have access to the [Call Graph Context], which lists the Called Methods (Callees) — i.e., methods that are directly invoked by the [Target Method], and the Calling Methods (Callers) — i.e., methods that invoke the [Target Method]. The Called Methods and Calling Methods are structured as a list of comma-separated callees and callers, respectively. Analyze the `signature` and `file_path` of each Called Method (or Calling Method) to deduce their specific functionality. Use this insight to infer the [Target Method]'s role within the overall call graph. Synthesize the above information  to explain what the method does and how it fits into the class's responsibility.

</task_scenario>

<input_data>
[Target Method]
Method Signature: 
{signature}

Method Body:
{body}

[Class Context]

- Class Name: {class_name}
- File Path: {file_path}
- Field List: {field_list}
- Sibling Methods: {sibling_methods}

[Call Graph Context]
- Called Methods (Callees): 
{callees}
- Calling Methods (Callers): 
{callers}

</input_data>

Generate the JSON summary based on the Method Signature and Method Body of the [Target Method], the [Class Context], and the Called Methods and the Calling Methods of [Target Method]'s [Call Graph Context].



## Reconstruction Prompt


You are a Java Code Generator.
Your task is to write the method body for the provided method's Signature and Summary.
You can get a sense of the code style through the following three examples:

<examples>

{examples_text}

</examples>

The signature and summary of the target method are as follows:

### Target

Method Signature: {signature}

Method Summary: {summary}

**Output**: Return **ONLY** the Java code block for the method body.
