# NFL Big Data Bowl 2026: The Void Engine

## Project Overview
This project introduces the "Void Engine" framework for grading defender effort in NFL zone coverage. It uses advanced tracking data to measure how defenders close space during ball flight, with metrics like VIS (Void Improvement Score) and CEOE (Closing Efficiency Over Expectation). The pipeline is designed for competition-ready analysis, coach/fan accessibility, and reproducible results.

## Architecture Diagram
![Pipeline Diagram](https://raw.githubusercontent.com/vserifoglu/NFL-Big-Data-Compeition/refs/heads/main/docs/pipeline_diagram.png)
*Figure - Data Engineering Pipeline Diagram*

## Project File Tree
```text
├── LICENSE
├── README.md
├── requirements.txt
├── writeup_steps.md
├── data/
│   ├── cleaned_dataset_columns.md
│   ├── physics_vars_inspection.txt
│   ├── processed/
│   │   └── (processed_data.CSVs)
│   ├── raw_dataset.md
│   ├── raw_dataset_dropout_logic_inspection.txt
│   ├── raw_dataset_inspection.md
│   ├── raw_dataset_inspection_report.txt
│   └── train/
│       └── (input/output CSVs)
├── docs/
│   ├── charts.md
│   ├── pipeline_diagram.png
│   └── ...
├── llm_knowledge_base/
│   └── file_combiner.py
├── notebooks/
│   ├── EDA.ipynb
│   ├── formula_and_data_validation.ipynb
│   └── ...
├── src/
│   ├── analysis/
│   │   ├── orchestrator.py
│   │   ├── story_visual_engine.py
│   │   └── ...
│   ├── benchmarking_engine.py
│   ├── context_engine.py
│   ├── eraser_engine.py
│   ├── physics_engine.py
│   └── ...
├── static/
│   └── visuals/
│       ├── V1_Eraser_Landscape.png
│       ├── V4_Effort_Impact_Chart.png
│       ├── V6_Void_Effect_Completion.png
│       ├── Figure_Top_FS_Eraser.gif
│       ├── Figure_Bottom_FS_Eraser.gif
│       └── ...
├── tests/
│   ├── test_benchmarking_engine.py
│   ├── test_context_engine.py
│   └── ...
```

## How to Run the Project

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```


### 2. Run the Data Engineering Pipeline
```bash
python -m src.orchestrator
```

### 3. Run the Data Vis Pipeline
```bash
python -m src.analysis.orchestrator
```

Each pipeline is modular and can be customized via `src/config.py`. Data engineering outputs are saved in `data/processed/`, and visuals/animations in `static/visuals/` by default.

### 4. Generate Tables
After running the pipeline, you can generate tables and charts using:
```bash
python -m src.analysis.table_generator
```

### 5. Animation Example
Below is a sample animation showing elite defender effort:
<div align="center">
	<img src="https://raw.githubusercontent.com/vserifoglu/NFL-Big-Data-Compeition/refs/heads/main/static/visuals/Figure_Top_FS_Eraser.gif" alt="Andre Cisco Eraser GIF" />
	<br>
	<em>Andre Cisco: top eraser play, closing 12.5 yards in under 2 seconds.</em>
</div>

