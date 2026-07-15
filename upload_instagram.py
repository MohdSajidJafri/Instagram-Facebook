"""
Upload rendered GTA VI brainrot shorts to Instagram Reels automatically.
Uses Cloudinary to host the local video file and the official Meta/Instagram Graph API to publish the Reel.
Falls back gracefully to manual upload guidelines if credentials are not configured.
"""
from __future__ import annotations

import time
from pathlib import Path
import requests

import config

# We import cloudinary lazily to avoid startup errors if the library is not installed
# and the user is just using the pipeline without uploading.


def _manual_upload_fallback(video_path: Path, caption: str) -> str:
    """Fallback guidelines when Graph API credentials are not set."""
    print(f"\n📍 Your video is ready at: {video_path}")
    print(f"   Caption: {caption[:80]}...")
    print()
    print("=" * 60)
    print("📱 MANUAL UPLOAD REQUIRED (Graph API credentials missing)")
    print("=" * 60)
    print()
    print("Please upload the video manually:")
    print()
    print("   1. Open the Instagram app on your phone")
    print(f"   2. Upload: {video_path.name}")
    print("   3. Paste this caption:")
    print(f"      {caption}")
    print()
    print("Or use the browser:")
    print("   1. Go to instagram.com and log in")
    print("   2. Click + → Select video file")
    print(f"   3. Choose: {video_path}")
    print("   4. Add caption and post")
    print("=" * 60)
    return ""


def upload_reel(
    video_path: Path,
    caption: str = "",
    fb_caption: str = "",
) -> str:
    """
    Uploads a local short to Instagram Reels.
    Uses Cloudinary to temporarily host the video and the Meta Graph API to publish.
    """
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return ""

    # Check for required credentials
    has_cloudinary = all([
        config.CLOUDINARY_CLOUD_NAME,
        config.CLOUDINARY_API_KEY,
        config.CLOUDINARY_API_SECRET
    ])
    has_ig_graph = all([
        config.IG_ACCESS_TOKEN,
        config.IG_ACCOUNT_ID
    ])

    if not (has_cloudinary and has_ig_graph):
        print("⚠ Instagram Graph API / Cloudinary credentials not fully configured.")
        return _manual_upload_fallback(video_path, caption)

    import cloudinary
    import cloudinary.uploader

    # Configure Cloudinary
    cloudinary.config(
        cloud_name=config.CLOUDINARY_CLOUD_NAME,
        api_key=config.CLOUDINARY_API_KEY,
        api_secret=config.CLOUDINARY_API_SECRET,
        secure=True
    )

    cloudinary_public_id = None
    cloudinary_url = None

    try:
        # Step 1: Upload the local video file to Cloudinary
        print(f"⏳ Uploading {video_path.name} to Cloudinary...")
        upload_result = cloudinary.uploader.upload_large(
            str(video_path),
            resource_type="video",
            folder="instagram_shorts_pipeline"
        )
        cloudinary_url = upload_result.get("secure_url")
        cloudinary_public_id = upload_result.get("public_id")
        print(f"   ✅ Cloudinary upload successful. Public URL: {cloudinary_url}")

        # Step 2: Create Meta Media Container for Reels
        print("⏳ Creating Instagram Reels container on Graph API...")
        version = config.IG_API_VERSION or "v20.0"
        container_url = f"https://graph.facebook.com/{version}/{config.IG_ACCOUNT_ID}/media"
        payload = {
            "media_type": "REELS",
            "video_url": cloudinary_url,
            "caption": caption,
            "access_token": config.IG_ACCESS_TOKEN
        }
        response = requests.post(container_url, data=payload)
        res_json = response.json()
        
        if "id" not in res_json:
            raise Exception(f"Failed to create media container: {res_json.get('error', {}).get('message', 'Unknown error')}")

        creation_id = res_json["id"]
        print(f"   ✅ Container created successfully. ID: {creation_id}")

        # Step 3: Poll Meta processing status
        status_url = f"https://graph.facebook.com/{version}/{creation_id}"
        params = {
            "fields": "status_code",
            "access_token": config.IG_ACCESS_TOKEN
        }
        
        print("⏳ Waiting for Instagram to process the video (polling)...")
        max_attempts = 30
        for attempt in range(max_attempts):
            res = requests.get(status_url, params=params)
            if res.status_code != 200:
                print(f"   ⚠ Status check request failed (HTTP {res.status_code}): {res.text}")
                time.sleep(10)
                continue
                
            status_res = res.json()
            status_code = status_res.get("status_code")
            
            if status_code == "FINISHED":
                print("   ✅ Video processing completed successfully!")
                break
            elif status_code in ["ERROR", "FAILED"]:
                # If there's a processing error, it might be in the container object description
                error_msg = status_res.get("error", {}).get("message", "No details")
                raise Exception(f"Video processing failed on Meta's servers: {error_msg}")
            
            print(f"   ⏳ Status: '{status_code}' (attempt {attempt+1}/{max_attempts}). Waiting 10s...")
            time.sleep(10)
        else:
            raise TimeoutError("Video processing timed out on Meta's servers.")

        # Step 4: Publish the Reel on Instagram
        print("⏳ Publishing the Reel on Instagram...")
        publish_url = f"https://graph.facebook.com/{version}/{config.IG_ACCOUNT_ID}/media_publish"
        publish_payload = {
            "creation_id": creation_id,
            "access_token": config.IG_ACCESS_TOKEN
        }
        publish_res = requests.post(publish_url, data=publish_payload).json()
        
        if "id" not in publish_res:
            raise Exception(f"Failed to publish Reel: {publish_res.get('error', {}).get('message', 'Unknown error')}")

        media_id = publish_res["id"]
        print(f"   🎉 Reel published successfully on Instagram! Media ID: {media_id}")

        # Step 5: Publish the Reel on Facebook Page (Optional/Additional)
        fb_access_token = config.FB_PAGE_ACCESS_TOKEN or config.IG_ACCESS_TOKEN
        if config.FB_PAGE_ID and fb_access_token:
            try:
                print("⏳ Initiating Facebook Page Reels upload session...")
                fb_url = f"https://graph.facebook.com/{version}/{config.FB_PAGE_ID}/video_reels"
                init_payload = {
                    "upload_phase": "start",
                    "access_token": fb_access_token
                }
                fb_init_res = requests.post(fb_url, data=init_payload).json()
                
                if "video_id" not in fb_init_res or "upload_url" not in fb_init_res:
                    raise Exception(f"Failed to initialize Facebook upload session: {fb_init_res.get('error', {}).get('message', 'Unknown error')}")
                
                fb_video_id = fb_init_res["video_id"]
                fb_upload_url = fb_init_res["upload_url"]
                print(f"   Facebook upload session initialized. Video ID: {fb_video_id}")
                
                print("⏳ Uploading video URL to Facebook Page...")
                upload_headers = {
                    "Authorization": f"OAuth {fb_access_token}",
                    "file_url": cloudinary_url
                }
                fb_upload_res = requests.post(fb_upload_url, headers=upload_headers).json()
                
                if not fb_upload_res.get("success", False) and "video_id" not in fb_upload_res:
                    raise Exception(f"Facebook upload failed: {fb_upload_res.get('error', {}).get('message', 'Unknown error')}")
                
                print("   Facebook upload complete. Finalizing Reel publication...")
                fb_desc = fb_caption or caption
                finish_payload = {
                    "upload_phase": "finish",
                    "access_token": fb_access_token,
                    "video_id": fb_video_id,
                    "video_state": "PUBLISHED",
                    "description": fb_desc
                }
                fb_publish_res = requests.post(fb_url, data=finish_payload).json()
                
                if not fb_publish_res.get("success", False):
                    raise Exception(f"Failed to publish Facebook Reel: {fb_publish_res.get('error', {}).get('message', 'Unknown error')}")
                
                print(f"   🎉 Reel published successfully on Facebook Page! Video ID: {fb_video_id}")
            except Exception as e:
                print(f"❌ Facebook Page Reels upload failed: {e}")

        return str(media_id)

    except Exception as e:
        print(f"❌ Automated Instagram upload / publishing failed: {e}")
        print("Falling back to manual instruction prompt...")
        _manual_upload_fallback(video_path, caption)
        return ""

    finally:
        # Step 5: Clean up Cloudinary asset to keep storage clean
        if cloudinary_public_id:
            print("🧹 Cleaning up temporary Cloudinary video asset...")
            try:
                cloudinary.uploader.destroy(cloudinary_public_id, resource_type="video")
                print("   ✅ Cloudinary temporary video asset deleted.")
            except Exception as e:
                print(f"   ⚠ Failed to delete Cloudinary asset {cloudinary_public_id}: {e}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True, help="Path to MP4")
    ap.add_argument("--caption", default="GTA VI BRAINROT 🎮🔥 #shorts #gta6", help="Reel caption")
    args = ap.parse_args()

    upload_reel(Path(args.video), args.caption)