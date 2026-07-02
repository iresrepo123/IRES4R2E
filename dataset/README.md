# Dataset Construction

While CodeSearchNet provides the necessary method-level metadata, it lacks the comprehensive contextual information required to investigate our research questions. To bridge this gap, we must trace each method back to its originating project to extract the relevant context. However, processing the entire CodeSearchNet Java partition---which encompasses 4,769 projects and 496,688 methods---is computationally prohibitive for large-scale LLM experiments. Consequently, we constructed a representative subset through a systematic seven-step pipeline:
1. We mapped each Java method in CodeSearchNet back to its original repository using the provided URLs in the method metadata;
2. We aggregated the method counts per project and ranked them in descending order;
3. We excluded projects that failed to parse correctly or fell outside the acceptable size threshold (i.e., those with $\le1,000$ or $\ge20,000$ methods);
4. To ensure broad representativeness, we selected a diverse set of 14 projects spanning various application domains;
5. We extracted all valid Java methods belonging to these 14 projects to form our initial dataset;
6. We cleaned the initial dataset following the data-cleaning procedure recommended by Zhou et al.~\cite{zhou2024learning}, including removing duplicate, empty, or abstract methods, methods lacking summaries or containing fewer than two statements, test code, and auto-generated source files;
7. We randomly sampled a balanced number of methods from each project (i.e., opencms-core and thredds contributed 358 methods each, while the remaining 12 projects contributed 357 methods each), yielding a final dataset of 5,000 methods (cf. Table~\ref{tab:dataset}).

Unless otherwise specified, all empirical evaluations in this study are conducted on this final dataset.

**Specifically:**
We first downloaded the Java subset of CodeSearchNet from Hugging Face and saved it as `my_java_data.json`. Because the source file is larger than 1.5 GB, it is not included in this repository. It can be downloaded and exported locally by running:

```bash
python get_dataset.py
```

After downloading the dataset, we used `countrepo.py` to count the number of functions associated with each repository. The script prints the 50 repositories containing the largest numbers of functions in descending order:

```bash
python countrepo.py
```

We then examined the GitHub repositories of these projects to identify their application domains. From them, we selected the following 14 repositories:

1. `Unidata/thredds`
2. `alkacon/opencms-core`
3. `apache/flink`
4. `apache/groovy`
5. `cdk/cdk`
6. `deeplearning4j/deeplearning4j`
7. `elki-project/elki`
8. `facebookarchive/hadoop-20`
9. `google/error-prone-javac`
10. `google/j2objc`
11. `hazelcast/hazelcast`
12. `lessthanoptimal/BoofCV`
13. `looly/hutool`
14. `zaproxy/zaproxy`

These projects cover a diverse range of application domains, and our preliminary tests confirmed that all of them could be parsed by Joern. We used `extract_and_split.py` to extract the CodeSearchNet entries belonging to each selected project and save them as separate project-level files in `selected_projects_json`:

```bash
python extract_and_split.py
```

Next, we used `query_context.sc` with Joern to extract contextual information for the functions. The resulting project-level files are stored in `projects_json_context`.

Finally, we used `sample_dataset.py` to select 5,000 functions while balancing the number of functions drawn from each project as evenly as possible. The script uses a fixed random seed of 42 by default to make the sampling process reproducible:

```bash
python sample_dataset.py
```

The resulting dataset is saved as `dataset.json`.

