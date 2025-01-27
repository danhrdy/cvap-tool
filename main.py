import argparse
from pathlib import Path
import sys
from src.transform import process_files
from src.analyze import analyze_dataset
from src.report import generate_report

def find_file_pairs(input_dir):
    # get matching pairs of files to combine eaf and json
    pairs = []
    xml_files = Path(input_dir).glob("*.eaf")
    
    for xml_path in xml_files:
        json_path = xml_path.with_suffix('.json')
        if json_path.exists():
            pairs.append((xml_path, json_path))
    
    return pairs

def process_single_dataset(xml_path, json_path, output_dir):
    # dataset processing and report generation function
    print(f"Processing {xml_path.name} and {json_path.name}")
    
    # data wrangling from transformation engine package
    df, metadata = process_files(xml_path, json_path)
    
    # get graphs and charts analysed
    results, analyzer = analyze_dataset(df, metadata)
    
    # analyzer visualizations
    viz_dir = analyzer.generate_all_visualizations(output_dir)
    static_dir = analyzer.create_static_visualizations(output_dir)
    
    # final report generation from report generation package
    report_path = generate_report(results, viz_dir, output_dir)
    
    return report_path

def main():
    parser = argparse.ArgumentParser(description='Computer Vision Analysis Profiling Tool')
    parser.add_argument('--mode', choices=['single', 'compare'], required=True,
                       help='Analysis mode: single dataset or compare multiple')
    parser.add_argument('--input', required=True,
                       help='Input directory containing EAF/JSON pairs')
    parser.add_argument('--output', required=True,
                       help='Output directory for report')
    
    args = parser.parse_args()
    
    # create outpit dir
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # get input pairs
    file_pairs = find_file_pairs(args.input)
    if not file_pairs:
        print(f"No matching XML/JSON pairs found in {args.input}")
        sys.exit(1)
    
    if args.mode == 'single':
        if len(file_pairs) > 1:
            print("Multiple file pairs found. Using the first pair.")
        
        xml_path, json_path = file_pairs[0]
        report_path = process_single_dataset(xml_path, json_path, output_dir)
        print(f"\nReport generated: {report_path}")
        
    else:  # compare mode
        if len(file_pairs) < 2:
            print("At least two file pairs needed for comparison mode")
            sys.exit(1)
            
        print(f"Found {len(file_pairs)} file pairs for comparison")
        
        # Process each dataset
        reports = []
        for xml_path, json_path in file_pairs:
            dataset_dir = output_dir / xml_path.stem
            dataset_dir.mkdir(exist_ok=True)
            
            report_path = process_single_dataset(xml_path, json_path, dataset_dir)
            reports.append((xml_path.stem, report_path))
        
        # Generate index page linking to all reports
        index_path = output_dir / "index.html"
        with open(index_path, 'w') as f:
            f.write("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Computer Vision Analysis Profiling Tool</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .report-link { 
                        display: block;
                        margin: 10px 0;
                        padding: 10px;
                        background: #f5f5f5;
                        text-decoration: none;
                        color: #333;
                    }
                </style>
            </head>
            <body>
                <h1>Computer Vision Analysis Profiling Tool</h1>
            """)
            
            for name, report in reports:
                f.write(f'<a class="report-link" href="{name}/report.html">{name}</a>')
            
            f.write("</body></html>")
        
        print(f"\nIndex page generated: {index_path}")

if __name__ == "__main__":
    main()