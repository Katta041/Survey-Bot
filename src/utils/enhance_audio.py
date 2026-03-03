import os
import pandas as pd
import numpy as np
import noisereduce as nr
import soundfile as sf
import av
import framework_config as config

def load_audio_av_np(filepath):
    """Loads audio using PyAV, resamples to 16kHz, and returns numpy array."""
    try:
        container = av.open(filepath)
        audio_stream = container.streams.audio[0]
        
        resampler = av.AudioResampler(format='fltp', layout='mono', rate=16000)
        
        audio_frames = []
        for frame in container.decode(audio_stream):
            frame.pts = None
            resampled_frames = resampler.resample(frame)
            for r_frame in resampled_frames:
                audio_frames.append(r_frame.to_ndarray())
        
        resampled_frames = resampler.resample(None)
        if resampled_frames:
             for r_frame in resampled_frames:
                audio_frames.append(r_frame.to_ndarray())

        if not audio_frames:
             return None, None
             
        # Concatenate: av returns [channels, samples] or [samples]
        audio_data = np.concatenate(audio_frames, axis=1)
        
        # Flatten to 1D for mono processing
        if audio_data.ndim > 1 and audio_data.shape[0] == 1:
            audio_data = audio_data.squeeze()
            
        return audio_data, 16000
    except Exception as e:
        print(f"AV Load Error for {filepath}: {e}")
        return None, None

def enhance_audio_samples():
    metadata_path = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'downloaded_metadata.csv')
    if not os.path.exists(metadata_path):
        print("Metadata file not found. Run downloader first.")
        return

    df = pd.read_csv(metadata_path)
    print(f"Enhancing {len(df)} files...")

    enhanced_files = []

    for index, row in df.iterrows():
        filepath = row['file_path']
        sample_id = row['sample_id']
        
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            enhanced_files.append("")
            continue

        print(f"Processing {sample_id}...")
        
        try:
            # Load audio using AV
            y, sr = load_audio_av_np(filepath)
            
            if y is None:
                raise Exception("Failed to load audio with AV")
            
            # 1. Noise Reduction (Spectral Gating)
            # Assuming the noise profile is stationary (hiss, hum)
            # We use a conservative reduction to avoid artifacts
            # noisereduce expects [samples] for mono
            reduced_noise = nr.reduce_noise(y=y, sr=sr, stationary=True, prop_decrease=0.75)
            
            # 2. Normalization
            # Normalize to -3dB
            max_val = np.max(np.abs(reduced_noise))
            if max_val > 0:
                target_db = -3.0
                target_amp = 10 ** (target_db / 20)
                norm_factor = target_amp / max_val
                normalized_audio = reduced_noise * norm_factor
            else:
                normalized_audio = reduced_noise

            # Save enhanced file
            dir_name = os.path.dirname(filepath)
            base_name = os.path.basename(filepath)
            name_part, ext_part = os.path.splitext(base_name)
            
            # Save as WAV for compatibility (soundfile writes wav easily)
            new_filename = f"{name_part}_cleaned.wav"
            new_filepath = os.path.join(dir_name, new_filename)
            
            sf.write(new_filepath, normalized_audio, sr)
            print(f"  > Saved to {new_filename}")
            
            enhanced_files.append(new_filepath)
            
        except Exception as e:
            print(f"Error enhancing {sample_id}: {e}")
            enhanced_files.append("")

    # Update metadata with new file paths
    # Keep original path, update 'file_path' to point to cleaned version for downstream scripts
    df['original_file_path'] = df['file_path']
    df['file_path'] = enhanced_files
    
    # Remove empty entries if enhancement failed
    df = df[df['file_path'] != ""]
    
    output_csv = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'enhanced_metadata.csv')
    df.to_csv(output_csv, index=False)
    print(f"Enhancement complete. Saved metadata to {output_csv}")

if __name__ == "__main__":
    enhance_audio_samples()
