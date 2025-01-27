
import xml.etree.ElementTree as ET
import json
import pandas as pd
from pathlib import Path

def parse_state_relationship(state):
    """Extract state and object from annotation value."""
    if not state:
        return None, None
    
    # Handle cases like "occluded_by(car1, car2)"
    if '(' in state and ')' in state:
        action = state.split('(')[0]
        content = state.split('(')[1].rstrip(')')
        
        # Check if there are multiple entities
        if ',' in content:
            entities = [e.strip() for e in content.split(',')]
            # Take the last entity as the object
            return action, entities[-1]
        else:
            # Single entity case like "visible(car1)"
            return action, None
            
    return state, None

def get_video_metadata(json_data):
    """Extract video metadata from JSON."""
    first_annotation = json_data['annotations'][0]
    first_result = first_annotation['result'][0]
    
    sequence = first_result['value']['sequence']
    duration = first_result['value']['duration']
    
    # Get total frames
    total_frames = max(frame['frame'] for frame in sequence)
    
    # Calculate FPS using first two frames
    frame1, frame2 = sequence[0], sequence[1]
    fps = 1 / (frame2['time'] - frame1['time'])
    
    return {
        'duration': duration,
        'total_frames': total_frames,
        'fps': fps
    }

def parse_label_studio_json(file_path):
    """Parse JSON file to get bounding box data."""
    with open(file_path) as f:
        json_data = json.load(f)
    
    metadata = get_video_metadata(json_data)
    bbox_data = []
    
    for annotation in json_data.get('annotations', []):
        for result in annotation.get('result', []):
            if result.get('type') == 'videorectangle':
                sequence = result.get('value', {}).get('sequence', [])
                entity = result.get('meta', {}).get('text', ['unknown'])[0]
                
                for frame_data in sequence:
                    bbox_data.append({
                        'frame': frame_data.get('frame'),
                        'timestamp': frame_data.get('time'),
                        'entity': entity,
                        'bbox_x': frame_data.get('x'),
                        'bbox_y': frame_data.get('y'),
                        'bbox_width': frame_data.get('width'),
                        'bbox_height': frame_data.get('height'),
                        'bbox_enabled': frame_data.get('enabled', True)
                    })
    
    return pd.DataFrame(bbox_data), metadata

def expand_annotation_to_frames(row, fps, total_frames):
    """Expand single annotation to cover all relevant frames."""
    start_frame = max(1, int(row['timestamp_start'] * fps) + 1)
    end_frame = min(int(row['timestamp_end'] * fps) + 1, total_frames + 1)
    
    frames = range(start_frame, end_frame)
    
    return pd.DataFrame({
        'frame': frames,
        'timestamp': [f/fps for f in frames],
        'entity': row['entity'],
        'category': row['category'],
        'state': row['state'],
        'object': row['object']
    })

def parse_elan_xml(file_path, fps, total_frames):
    """Parse XML file to get annotations."""
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # Get time slots mapping
    time_slots = {
        slot.get('TIME_SLOT_ID'): float(slot.get('TIME_VALUE', 0))/1000.0 
        for slot in root.findall('.//TIME_SLOT')
    }
    
    annotations = []
    
    for tier in root.findall('.//TIER'):
        tier_id = tier.get('TIER_ID')
        if '(' not in tier_id or ')' not in tier_id:
            continue
            
        category, entity = tier_id.split('(')
        entity = entity.rstrip(')')
        
        for annotation in tier.findall('.//ALIGNABLE_ANNOTATION'):
            start_slot = annotation.get('TIME_SLOT_REF1')
            end_slot = annotation.get('TIME_SLOT_REF2')
            value = annotation.find('ANNOTATION_VALUE').text
            
            try:
                if start_slot in time_slots and end_slot in time_slots:
                    state, object_entity = parse_state_relationship(value)
                    
                    row = {
                        'timestamp_start': time_slots[start_slot],
                        'timestamp_end': time_slots[end_slot],
                        'entity': entity,
                        'category': category,
                        'state': state,
                        'object': object_entity
                    }
                    
                    frame_rows = expand_annotation_to_frames(row, fps, total_frames)
                    annotations.append(frame_rows)
            except Exception as e:
                print(f"Error processing annotation: {value}")
                print(f"In tier: {tier_id}")
                print(f"Error: {str(e)}")
                raise
    
    return pd.concat(annotations, ignore_index=True) if annotations else pd.DataFrame()

def create_base_dataframe(metadata, bbox_df):
    """Create base DataFrame with all frame-entity combinations."""
    entities = bbox_df['entity'].unique()
    frames = range(1, metadata['total_frames'] + 1)
    
    frame_entity_pairs = [(frame, entity) 
                         for frame in frames 
                         for entity in entities]
    
    base_df = pd.DataFrame(frame_entity_pairs, columns=['frame', 'entity'])
    base_df['timestamp'] = base_df['frame'] / metadata['fps']
    
    return base_df

def process_files(xml_path, json_path):
    """Process XML and JSON files and return combined DataFrame."""
    # Get bounding box data and metadata
    bbox_df, metadata = parse_label_studio_json(json_path)
    
    # Create base DataFrame with all frames
    base_df = create_base_dataframe(metadata, bbox_df)
    
    # Get annotations
    xml_df = parse_elan_xml(xml_path, metadata['fps'], metadata['total_frames'])
    
    # Merge bounding box data
    with_bbox = pd.merge(
        base_df,
        bbox_df,
        on=['frame', 'entity', 'timestamp'],
        how='left'
    )
    
    # Merge annotations if they exist
    if not xml_df.empty:
        final_df = pd.merge(
            with_bbox,
            xml_df,
            on=['frame', 'entity', 'timestamp'],
            how='left'
        )
    else:
        final_df = with_bbox
        final_df['category'] = None
        final_df['state'] = None
        final_df['object'] = None
    
    # Mark frames with/without annotations
    final_df['has_annotation'] = ~final_df['state'].isna()
    
    return final_df, metadata

if __name__ == "__main__":
    # Test with sample files
    xml_path = "./data/sample/sample_1.eaf"
    json_path = "./data/sample/sample_1.json"
    
    df, metadata = process_files(xml_path, json_path)
    print("Video metadata:", metadata)
    print("\nDataFrame shape:", df.shape)
    print("\nColumns:", df.columns.tolist())
    print("\nSample data:")
    print(df.head())