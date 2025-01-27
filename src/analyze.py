import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

class VideoAnalyzer:
    def __init__(self, df, metadata):
        self.df = df
        self.metadata = metadata
        self.entities = df['entity'].unique()
        
    def get_basic_stats(self):
        # calculating basic video statistics : duration, frame count, number of entities
        return {
            'duration': self.metadata['duration'],
            'total_frames': self.metadata['total_frames'],
            'fps': self.metadata['fps'],
            'total_entities': len(self.entities),
            'annotation_coverage': len(self.df[self.df['has_annotation']]) / len(self.df)
        }

    def create_static_visualizations(self, output_dir):
        # static graphs with matplotlib and seaborn
        
        static_dir = Path(output_dir) / "static_plots"
        static_dir.mkdir(exist_ok=True)
        
        # 1. Timeline of annotations per entity
        plt.figure(figsize=(15, 8))
        for i, entity in enumerate(self.entities):
            entity_df = self.df[self.df['entity'] == entity]
            plt.plot(entity_df['timestamp'], 
                    [i] * len(entity_df), 
                    'o', 
                    label=entity,
                    alpha=0.5)
        plt.yticks(range(len(self.entities)), self.entities)
        plt.title("Entity Presence Timeline")
        plt.xlabel("Time (seconds)")
        plt.tight_layout()
        plt.savefig(static_dir / "entity_timeline.png")
        plt.close()
        
        # 2. Bounding box trajectories
        plt.figure(figsize=(10, 10))
        for entity in self.entities:
            entity_df = self.df[self.df['entity'] == entity]
            plt.plot(entity_df['bbox_x'], 
                    entity_df['bbox_y'], 
                    '-', 
                    label=entity,
                    alpha=0.5)
        plt.title("Entity Trajectories")
        plt.xlabel("X position")
        plt.ylabel("Y position")
        plt.legend()
        plt.tight_layout()
        plt.savefig(static_dir / "trajectories.png")
        plt.close()
        
        # 3. State distribution heatmap
        state_matrix = []
        for entity in self.entities:
            entity_df = self.df[self.df['entity'] == entity]
            state_counts = entity_df['state'].value_counts()
            state_matrix.append(state_counts)
        
        state_df = pd.DataFrame(state_matrix, index=self.entities)
        plt.figure(figsize=(12, 8))
        sns.heatmap(state_df, annot=True, fmt='g', cmap='YlOrRd')
        plt.title("State Distribution per Entity")
        plt.tight_layout()
        plt.savefig(static_dir / "state_heatmap.png")
        plt.close()
        
        return static_dir

    def analyze_entity_states(self, entity):
        # analyzing states for different entities
        entity_df = self.df[self.df['entity'] == entity]
        
        states = entity_df[entity_df['state'].notna()].groupby('state').size()
        categories = entity_df[entity_df['category'].notna()].groupby('category').size()
        
        return {
            'total_frames': len(entity_df),
            'annotated_frames': len(entity_df[entity_df['has_annotation']]),
            'states': states.to_dict(),
            'categories': categories.to_dict()
        }
    
    def create_entity_timeline(self, output_dir):
        # create timeline visualization for all entities
        fig = go.Figure()
        
        for entity in self.entities:
            entity_df = self.df[self.df['entity'] == entity]
            states = entity_df[entity_df['state'].notna()]['state'].unique()
            
            for state in states:
                state_df = entity_df[entity_df['state'] == state]
                fig.add_trace(go.Scatter(
                    x=state_df['timestamp'],
                    y=[entity] * len(state_df),
                    mode='markers',
                    name=f"{entity}-{state}",
                    marker=dict(size=5)
                ))
        
        fig.update_layout(
            title="Entity States Timeline",
            xaxis_title="Time (seconds)",
            yaxis_title="Entity",
            height=400 * len(self.entities)
        )
        
        fig.write_html(Path(output_dir) / "entity_timeline.html")
    
    def create_state_distribution(self, output_dir):
		# per entity state distribution
        for entity in self.entities:
            entity_df = self.df[self.df['entity'] == entity]
            state_counts = entity_df[entity_df['state'].notna()]['state'].value_counts()
            
            fig = px.pie(
                values=state_counts.values,
                names=state_counts.index,
                title=f"State Distribution for {entity}"
            )
            
            fig.write_html(Path(output_dir) / f"state_dist_{entity}.html")
    
    def create_interaction_network(self, output_dir):
        # network graph of entity and object interaction
        import networkx as nx
        
        # create new network
        G = nx.DiGraph()
        
        # add interactions as edges
        interactions = self.df[self.df['object'].notna()]
        for _, row in interactions.iterrows():
            G.add_edge(row['entity'], row['object'], state=row['state'])
        
        # convert to plotly figure
        pos = nx.spring_layout(G)
        
        edge_trace = go.Scatter(
            x=[], y=[],
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines')
        
        node_trace = go.Scatter(
            x=[], y=[],
            mode='markers+text',
            hoverinfo='text',
            text=[],
            marker=dict(size=20))
        
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_trace['x'] += (x0, x1, None)
            edge_trace['y'] += (y0, y1, None)
        
        for node in G.nodes():
            x, y = pos[node]
            node_trace['x'] += (x,)
            node_trace['y'] += (y,)
            node_trace['text'] += (node,)
        
        fig = go.Figure(data=[edge_trace, node_trace],
                     layout=go.Layout(
                         title='Entity Interaction Network',
                         showlegend=False,
                         hovermode='closest',
                         margin=dict(b=20,l=5,r=5,t=40)
                     ))
        
        fig.write_html(Path(output_dir) / "interaction_network.html")
    
    def create_bounding_box_movement(self, output_dir):
        # heatmap of entity movements from bounding box data
        for entity in self.entities:
            entity_df = self.df[self.df['entity'] == entity]
            
            fig = go.Figure(data=go.Heatmap(
                x=entity_df['bbox_x'],
                y=entity_df['bbox_y'],
                z=entity_df['frame'],
                colorscale='Viridis'
            ))
            
            fig.update_layout(
                title=f"Movement Heatmap for {entity}",
                xaxis_title="X position",
                yaxis_title="Y position"
            )
            
            fig.write_html(Path(output_dir) / f"movement_{entity}.html")
    
    def generate_all_visualizations(self, output_dir):
        # generate all visualizations
        output_dir = Path(output_dir) / "visualizations"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.create_entity_timeline(output_dir)
        self.create_state_distribution(output_dir)
        self.create_interaction_network(output_dir)
        self.create_bounding_box_movement(output_dir)
        
        return output_dir

def analyze_dataset(df, metadata):
    # main analysis function
    analyzer = VideoAnalyzer(df, metadata)
    
    results = {
        'basic_stats': analyzer.get_basic_stats(),
        'entity_stats': {
            entity: analyzer.analyze_entity_states(entity)
            for entity in analyzer.entities
        }
    }
    
    return results, analyzer