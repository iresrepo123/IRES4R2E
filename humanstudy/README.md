# Human Experimental Procedure

Because of the substantial workload involved in the human evaluation, we divided the 500 functions into 20 batches. Each batch contained 25 code-summary ranking tasks. We recruited five developers, each with more than three years of Java development experience, and instructed them on how to use our lightweight code-summary ranking platform (`annotation_app`). On the platform, the summaries corresponding to strategies L1–L9 (in the paper, we used C1-C9) were shuffled and presented anonymously to the participants using the labels A–I. For each function, the participants were required to rank all nine summaries, from A to I, according to the evaluation criteria defined in `Evaluation criteria.md`. The participants were strictly instructed not to discuss the tasks or their rankings with one another. After collecting the data, we used the recorded label-to-strategy mapping to recover the context strategy represented by each anonymous label. The developers were assigned the participant IDs 101, 102, 103, 104, and 105. Each participant independently ranked the summaries for all 500 functions. The rankings submitted by all participants were consolidated into `human_data.csv`.

Consequently, we obtained five summary-ranking sequences for each function. Each sequence contained nine summaries generated using the nine context strategies. For each summary, we calculated its final score as the mean of the ranks assigned by the five evaluators. For example, if the summary generated using strategy L3 received ranks of 7, 4, 6, 2, and 7, its final score was calculated as:

$$
\frac{7 + 4 + 6 + 2 + 7}{5} = 5.2
$$

We then ranked all nine summaries for each function according to their final scores, assigning positions from 1 to 9. When two or more strategies had the same final score, we assigned them the average of the positions they occupied. For example, if the summaries generated using strategies L7 and L3 both had a final score of 5.2 and jointly occupied positions 4 and 5, both were assigned a final rank of:

$$
\frac{4 + 5}{2} = 4.5
$$

Finally, this procedure produced `human_rank_final.csv`, which contains the aggregated human-evaluation rankings for all 500 functions.


In the evaluation, each developer will read a Java method and rank nine candidate summaries from best to worst. Candidate labels are randomized and do not reveal their source configuration.

## Evaluation criteria

- **Coherence:** the summary is logically organized and understandable.
- **Consistency:** every claim is supported by the code; penalize hallucinated behavior.
- **Fluency:** the summary is grammatical, readable, and natural.
- **Relevance:** it focuses on the method's main intent and important operations.

Drag summaries to create a complete ranking: position 1 is best and position 9 is worst. You may pause and resume on the same browser.