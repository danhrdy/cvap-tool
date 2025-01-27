from jinja2 import Template
from pathlib import Path

# report template 
def generate_report(results, viz_dir, output_dir):
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CVAP Tool</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; }
            .visualization { margin: 20px 0; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
            .stat-card { 
                padding: 15px; 
                background: #f5f5f5; 
                border-radius: 5px;
                text-align: center;
            }
            .tabs { display: flex; margin: 20px 0; }
            .tab { 
                padding: 10px 20px; 
                cursor: pointer; 
                border: 1px solid #ddd;
                background: #f5f5f5;
            }
            .tab.active { background: #fff; border-bottom: none; }
            .tab-content { display: none; }
            .tab-content.active { display: block; }
        </style>
    </head>
    <body>
        <h1>Computer Vision Analysis Profiling Tool</h1>
        
        <div class="section">
            <h2>Basic Statistics</h2>
            <div class="stats">
                {% for key, value in basic_stats.items() %}
                <div class="stat-card">
                    <h3>{{ key|replace('_', ' ')|title }}</h3>
                    <p>{{ "%.2f"|format(value) if value is float else value }}</p>
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="section">
            <h2>Entity Analysis</h2>
            <div class="tabs">
                {% for entity in entities %}
                <div class="tab" onclick="showTab('{{ entity }}')">{{ entity }}</div>
                {% endfor %}
            </div>
            
            {% for entity in entities %}
            <div id="{{ entity }}" class="tab-content">
                <h3>{{ entity }} Statistics</h3>
                <div class="visualization">
                    <h4>State Distribution</h4>
                    <iframe src="visualizations/state_dist_{{ entity }}.html" width="100%" height="400px"></iframe>
                </div>
                <div class="visualization">
                    <h4>Movement Heatmap</h4>
                    <iframe src="visualizations/movement_{{ entity }}.html" width="100%" height="400px"></iframe>
                </div>
                <div class="visualization">
                    <h4>Static Visualizations</h4>
                    <img src="static_plots/trajectories.png" width="100%">
                </div>
            </div>
            {% endfor %}
        </div>

        <div class="section">
            <h2>Timeline Analysis</h2>
            <div class="visualization">
                <iframe src="visualizations/entity_timeline.html" width="100%" height="600px"></iframe>
            </div>
        </div>

        <div class="section">
            <h2>Interaction Network</h2>
            <div class="visualization">
                <iframe src="visualizations/interaction_network.html" width="100%" height="600px"></iframe>
            </div>
        </div>

        <script>
            function showTab(entityId) {
                // Hide all tab contents
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.style.display = 'none';
                });
                // Show selected tab content
                document.getElementById(entityId).style.display = 'block';
                // Update active tab
                document.querySelectorAll('.tab').forEach(tab => {
                    tab.classList.remove('active');
                });
                document.querySelector(`[onclick="showTab('${entityId}')"]`).classList.add('active');
            }
            
            // Show first tab by default
            showTab('{{ entities[0] }}');
        </script>
    </body>
    </html>
    """
    
    # prepare template data
    template_data = {
        'basic_stats': results['basic_stats'],
        'entities': list(results['entity_stats'].keys()),
        'viz_dir': viz_dir
    }
    
    # generate report
    report_html = Template(template).render(**template_data)
    
    # write report to file
    report_path = Path(output_dir) / "report.html"
    with open(report_path, 'w') as f:
        f.write(report_html)
    
    return report_path