
import xml.etree.ElementTree as ET
import json
import pandas as pd
from pathlib import Path

def parse_state_relationship(state):
    # getting subject and object states and relationships
    if not state:
        return None, []
    # text parsing, getting information about entities and objects and their relationships 
    # handle list of objects like moving_towards(black_car, [ego_car, white_car])
    if '(' in state and ')' in state:
        action = state.split('(')[0]
        content = state.split('(')[1].rstrip(')')
        
        # if multiple objects in relationship (list)
        if '[' in content and ']' in content:
            # Split on comma first to get subject and list of objects
            subject_and_objects = content.split(',', 1)
            if len(subject_and_objects) > 1:
                objects_str = subject_and_objects[1].strip()
                objects_str = objects_str.strip('[]')
                objects = [obj.strip() for obj in objects_str.split(',')]
                return action, objects
        
        # 1:1 relationships (single entity, single object of action)
        elif ',' in content:
            entities = [e.strip() for e in content.split(',')]
            return action, [entities[-1]]  # Return as list for consistency
        else:
            # single entity like visible(car1)
            return action, []
            
    return state, []

def get_video_metadata(json_data):
    # json metadata extraction for overall information about files
    first_annotation = json_data['annotations'][0]
    first_result = first_annotation['result'][0]
    # duration, number of frames
    sequence = first_result['value']['sequence']
    duration = first_result['value']['duration']
    
    # total frames
    total_frames = max(frame['frame'] for frame in sequence)
    
    # get fps
    frame1, frame2 = sequence[0], sequence[1]
    fps = 1 / (frame2['time'] - frame1['time'])
    
    return {
        'duration': duration,
        'total_frames': total_frames,
        'fps': fps
    }

def parse_label_studio_json(file_path):
    # json parsing for bounding box data (x, y cord + x, y width and height)
    with open(file_path) as f:
        json_data = json.load(f)
    
    metadata = get_video_metadata(json_data)
    bbox_data = []
    
    print("Parsing JSON annotations...")
    for annotation in json_data.get('annotations', []):
        for result in annotation.get('result', []):
            if result.get('type') == 'videorectangle':
                entity = result.get('meta', {}).get('text', ['unknown'])[0]
                print(f"Found entity in JSON: {entity}")
                sequence = result.get('value', {}).get('sequence', [])
                
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
    # stretching annotation to get it for all affected frames
    start_frame = max(1, int(row['timestamp_start'] * fps) + 1)
    end_frame = min(int(row['timestamp_end'] * fps) + 1, total_frames + 1)
    
    frames = range(start_frame, end_frame)
    frames_data = []
    
    # rows for each object in an annotation action
    if row['objects']:  # single row for each action, entity and object of relationship state
        for obj in row['objects']:
            for frame in frames:
                frames_data.append({
                    'frame': frame,
                    'timestamp': frame/fps,
                    'entity': row['entity'],
                    'category': row['category'],
                    'state': row['state'],
                    'object': obj
                })
    else:
        # in case of no objects (single entity state)
        for frame in frames:
            frames_data.append({
                'frame': frame,
                'timestamp': frame/fps,
                'entity': row['entity'],
                'category': row['category'],
                'state': row['state'],
                'object': None
            })
    
    return pd.DataFrame(frames_data)

def parse_elan_xml(file_path, fps, total_frames):
    # parsing XML to pull out annotations from EAF file
    tree = ET.parse(file_path)
    root = tree.getroot()
    
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
                    state, objects = parse_state_relationship(value)
                    
                    row = {
                        'timestamp_start': time_slots[start_slot],
                        'timestamp_end': time_slots[end_slot],
                        'entity': entity,
                        'category': category,
                        'state': state,
                        'objects': objects
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
    # base dataframe creation - per frame per entity
    entities = bbox_df['entity'].unique()
    frames = range(1, metadata['total_frames'] + 1)
    
    frame_entity_pairs = [(frame, entity) 
                         for frame in frames 
                         for entity in entities]
    
    base_df = pd.DataFrame(frame_entity_pairs, columns=['frame', 'entity'])
    base_df['timestamp'] = base_df['frame'] / metadata['fps']
    
    return base_df

def process_files(xml_path, json_path):
    # process EAF and JSON files
    # get metadata and bounding boxes - print out for check
    bbox_df, metadata = parse_label_studio_json(json_path)
    print("\nJSON DataFrame shape:", bbox_df.shape)
    print("JSON first few rows:")
    print(bbox_df.head())
    
    # all frames dataframe
    base_df = create_base_dataframe(metadata, bbox_df)
    print("\nBase DataFrame shape:", base_df.shape)
    
    # run transformation engine to get annotations
    xml_df = parse_elan_xml(xml_path, metadata['fps'], metadata['total_frames'])
    print("\nXML DataFrame shape:", xml_df.shape)
    print("XML first few rows:")
    print(xml_df.head())
    
    # merge bounding box data to base dataframe
    # rounding timestamps to ease up merging of dataframes
    bbox_df['timestamp'] = bbox_df['timestamp'].round(3)
    base_df['timestamp'] = base_df['timestamp'].round(3)
    
    print("\nAttempting merge with bounding box data...")
    with_bbox = pd.merge(
        base_df,
        bbox_df,
        on=['frame', 'entity'],  # removed timestamp from merge keys
        how='left'
    )
    print("\nAfter bbox merge shape:", with_bbox.shape)
    
    # update timestamp with bounding box
    with_bbox['timestamp'] = with_bbox['timestamp_y'].fillna(with_bbox['timestamp_x'])
    with_bbox = with_bbox.drop(['timestamp_x', 'timestamp_y'], axis=1)
    
    # timestamp rounding for EAF file merging
    if not xml_df.empty:
        xml_df['timestamp'] = xml_df['timestamp'].round(3)
        
        print("\nAttempting merge with ELAN annotations...")
        final_df = pd.merge(
            with_bbox,
            xml_df,
            on=['frame', 'entity'],  # removed timestamp from merge keys
            how='left'
        )
        
        # update timestamp from xml_df where available
        final_df['timestamp'] = final_df['timestamp_y'].fillna(final_df['timestamp_x'])
        final_df = final_df.drop(['timestamp_x', 'timestamp_y'], axis=1)
    else:
        final_df = with_bbox
        final_df['category'] = None
        final_df['state'] = None
        final_df['object'] = None
    
    # mark frames with/without annotations
    final_df['has_annotation'] = ~final_df['state'].isna()
    
    print("\nFinal DataFrame shape:", final_df.shape)
    print("Final DataFrame columns:", final_df.columns.tolist())
    
    return final_df, metadata

# testing and information printout
"""""
if __name__ == "__main__":
    # Test with sample files
    xml_path = "../data/sample/sample_1.eaf"
    json_path = "../data/sample/sample_1.json"
    
    df, metadata = process_files(xml_path, json_path)
    print("Video metadata:", metadata)
    print("\nDataFrame shape:", df.shape)
    print("\nColumns:", df.columns.tolist())
    print("\nSample data:")
    print(df.head())
"""""