# Dataset construction process
While CodeSearchNet provides the necessary method-level metadata, it lacks the comprehensive contextual information required to investigate our research questions. To bridge this gap, we must trace each method back to its originating project to extract the relevant context. However, processing the entire CodeSearchNet Java partition---which encompasses 4,769 projects and 496,688 methods---is computationally prohibitive for large-scale LLM experiments. Consequently, we constructed a representative subset through a systematic seven-step pipeline:
1. We mapped each Java method in CodeSearchNet back to its original repository using the provided URLs in the method metadata;
2. We aggregated the method counts per project and ranked them in descending order;
3. We excluded projects that failed to parse correctly or fell outside the acceptable size threshold (i.e., those with $\le1,000$ or $\ge20,000$ methods);
4. To ensure broad representativeness, we selected a diverse set of 14 projects spanning various application domains;
5. We extracted all valid Java methods belonging to these 14 projects to form our initial dataset;
6. We cleaned the initial dataset following the data-cleaning procedure recommended by Zhou et al.~\cite{zhou2024learning}, including removing duplicate, empty, or abstract methods, methods lacking summaries or containing fewer than two statements, test code, and auto-generated source files;
7. We randomly sampled a balanced number of methods from each project (i.e., opencms-core and thredds contributed 358 methods each, while the remaining 12 projects contributed 357 methods each), yielding a final dataset of 5,000 methods (cf. Table~\ref{tab:dataset}).

Unless otherwise specified, all empirical evaluations in this study are conducted on this final dataset.

**Our dataset is available at code\R2E\dataset**.
