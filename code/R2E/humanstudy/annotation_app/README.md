# Local RQ1 annotation app

This is a no-backend, local browser app for ranking nine blinded candidate summaries for each Java method.

## Prepare and open

From the repository root, generate the task package:

```bash
python3 RQ1/build_annotation_tasks.py
```

Then open `RQ1/annotation_app/index.html` in a modern desktop browser. No web server or account is required.

## Assigning work

The 500 methods are split into 20 fixed batches of 25 methods. Give each participant an anonymous ID and a batch number. To obtain multiple independent judgments for one method, assign the same batch to multiple participants; candidate labels are randomized independently for each participant.

## Collecting results

At the end of a batch the participant downloads `RQ1_annotation_<ID>_batch<N>.csv` and sends it to the researcher. Each row stores the participant ID, sample ID, final rank, displayed candidate label, hidden context level, time spent, and timestamp. The `context_level` column is essential for mapping the blinded ranking back to L1--L9; do not share it with participants.

Progress is stored only in the browser's local storage. Participants should use the same browser and device when resuming a partially completed batch, and should download their CSV before clearing browser data.
