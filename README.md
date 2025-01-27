# CVAP Tool
## This is the Computer Vision Analysis Profiling Tool

This tool allows for generated report creation, similar to already established tools like ydata-profiling (pandas-profiling) or sweetviz.

This set of scripts was created for the Human-Computer Interaction Class at the Örebro University in Sweden, fall semester 2024.

### What is it?
The CVAP tool is an example script that transforms .EAF (XML) and .JSON files into tabular structure and then creates a generated report on top of this table.

[EAF files come from ELAN](https://github.com/mxochicale/elan) and [JSON from Label Studio](https://labelstud.io). The goal is to take already-made video annotations (ELAN) and bounding box information about entities (Label Studio) and combine these files into easy to read visuals, ready for further analysis. This tool can work as a bridge between just made annotations as a error check (statistics about given dataset) and a continuation of work, using the transformation engine to get a tabular structure out of JSON and EAF files.


### Usage
Setup:
```console
dan@mbp:~$ pip install -r requirements.txt
```

To run:
```console
dan@mbp:~$ python main.py --mode (single/compare) --input ./data --output ./data/report
```

Your input directory needs to contain a pair of files with the same name, at least one .eaf and one .json file. 





