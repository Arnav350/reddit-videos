import sys
import praw
import time
import os
import random
from gtts import gTTS
import logging
from datetime import datetime, timezone, timedelta
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
from moviepy.video.tools.subtitles import SubtitlesClip

# Configure logging
logging.basicConfig(level=logging.INFO, filename='reddit_monitor.log', 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Replace with your own credentials
reddit = praw.Reddit(
    client_id='KHEPmPCMPQc1sAqR0GMUSQ',
    client_secret='b4R9SjFeRDomFncF7qacQoZfVD0Y1g',
    user_agent='aita-videos u/Conscious-Star-9156'
)

subreddit = reddit.subreddit('AmItheAsshole')

# Directory to save audio and video files
output_directory = 'AITA_output'
if not os.path.exists(output_directory):
    os.makedirs(output_directory)

# Directory containing video files
video_directory = 'AITA_videos'
video_files = [os.path.join(video_directory, f) for f in os.listdir(video_directory) if f.endswith('.mp4')]

# File to keep track of processed posts
processed_posts_file = 'processed_posts.txt'

# Load processed post IDs to avoid duplicates
if os.path.exists(processed_posts_file):
    with open(processed_posts_file, 'r') as f:
        processed_posts = set(line.strip() for line in f)
else:
    processed_posts = set()

def break_text_into_chunks(text, max_words=2):
    words = text.split()
    chunks = [' '.join(words[i:i + max_words]) for i in range(0, len(words), max_words)]
    return chunks

def create_audio_from_post(post):
    try:
        # Replace "AITA" with "Am I the asshole" in the title
        title = post.title.replace('AITA', 'Am I the asshole', 1)
        content = post.selftext.strip()

        # Create a string with the title and content separated by a pause
        text = f"{title}\n\n{content}"
        
        audio_path = f"{output_directory}/{post.id}.mp3"
        tts = gTTS(text, lang='en', tld='co.uk')  # Example: British English
        tts.save(audio_path)
        logging.info(f"Created audio for post: {post.id}")

        # Process the video
        process_video(audio_path, post.id, text)
    except Exception as e:
        logging.error(f"Error creating audio for post {post.id}: {e}")

def generate_subtitles(text, duration):
    chunks = break_text_into_chunks(text, max_words=2)
    subtitle_clips = []
    chunk_duration = duration / len(chunks)
    
    for i, chunk in enumerate(chunks):
        start_time = i * chunk_duration
        end_time = (i + 1) * chunk_duration
        txt_clip = (TextClip(chunk, fontsize=24, color='white', bg_color='black')
                    .set_position(('center', 'bottom'))
                    .set_start(start_time)
                    .set_end(end_time))
        subtitle_clips.append(txt_clip)
    
    return CompositeVideoClip(subtitle_clips)

def process_video(audio_path, post_id, text):
    try:
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration

        # Select a random video file
        video_file = random.choice(video_files)
        video_clip = VideoFileClip(video_file)
        video_duration = video_clip.duration

        # Ensure there is enough time left in the video for the entire audio clip
        max_start_time = video_duration - audio_duration
        start_time = random.uniform(0, max_start_time)

        # Trim the video and set the audio
        trimmed_video = video_clip.subclip(start_time, start_time + audio_duration)
        trimmed_video = trimmed_video.set_audio(audio_clip)

        # Generate subtitles
        subtitles = generate_subtitles(text, audio_duration)

        # Combine video and subtitles
        final_video = CompositeVideoClip([trimmed_video, subtitles])

        # Save the combined video
        output_path = f"{output_directory}/{post_id}.mp4"
        final_video.write_videofile(output_path, codec='libx264')
        logging.info(f"Created video for post: {post_id}")
    except Exception as e:
        logging.error(f"Error processing video for post {post_id}: {e}")

def monitor_subreddit():
    while True:
        try:
            suitable_post_found = False
            for post in subreddit.hot(limit=10):  # Use the hot sorting method and retrieve the top 10 posts
                # Skip stickied (pinned) posts
                if post.stickied:
                    continue
                
                # Check if the post is older than an hour using timezone-aware datetime objects
                post_age = datetime.now(timezone.utc) - datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                if post_age > timedelta(hours=1):
                    if post.id not in processed_posts:
                        create_audio_from_post(post)
                        with open(processed_posts_file, 'a') as f:
                            f.write(post.id + '\n')
                        processed_posts.add(post.id)
                        suitable_post_found = True
                        break  # Exit the loop after processing one post
            
            if not suitable_post_found:
                logging.info("No suitable post found. Waiting for the next check.")

            time.sleep(3600)  # Wait for an hour before checking again
        except Exception as e:
            logging.error(f"Error in monitoring loop: {e}")
            time.sleep(3600)  # Wait before retrying if an error occurs

if __name__ == "__main__":
    monitor_subreddit()
