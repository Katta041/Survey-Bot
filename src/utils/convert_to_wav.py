import av
import os
import sys

def convert_to_wav(input_path, output_path):
    print(f"Converting {input_path} -> {output_path}")
    try:
        with av.open(input_path) as input_container:
            in_stream = input_container.streams.audio[0]
            
            with av.open(output_path, 'w', 'wav') as output_container:
                out_stream = output_container.add_stream('pcm_s16le', rate=16000)
                # out_stream.layout = 'mono' # This might span multiple attrs depending on version
                # Correct way for newer PyAV might be adding options or setting channels
                # Let's try simpler add_stream if possible or keep as is but check error
                pass
                
                for frame in input_container.decode(in_stream):
                    for packet in out_stream.encode(frame):
                        output_container.mux(packet)
                
                # Flush
                for packet in out_stream.encode(None):
                    output_container.mux(packet)
                    
        print("Conversion successful.")
        return True
    except Exception as e:
        print(f"Conversion failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python convert_to_wav.py <input> <output>")
        # Default test
        base_dir = "/Users/aierarohit/Desktop/Political Data/audio_samples"
        input_f = os.path.join(base_dir, "Valid_45c3ab84-6136-4d54-9601-544bdb5d7c6d.mp3")
        output_f = os.path.join(base_dir, "debug_sample.wav")
        convert_to_wav(input_f, output_f)
    else:
        convert_to_wav(sys.argv[1], sys.argv[2])
