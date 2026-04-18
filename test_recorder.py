import asyncio
from playwright.async_api import async_playwright
import os
import time

async def record_html_bg(duration_sec=10, output_path="downloads/hexagon_bg.webm"):
    os.makedirs("downloads", exist_ok=True)
    if os.path.exists(output_path):
        os.remove(output_path)
        
    html_path = f"file://{os.path.abspath('hexagon_only.html')}"
    
    # We use webm because Playwright records webm natively very fast
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Invisible
        
        # 1080x1920 is vertical shorts resolution, but we can render 540x960 for speed 
        # and scale it up later in MoviePy
        context = await browser.new_context(
            record_video_dir="downloads/",
            record_video_size={"width": 540, "height": 960}
        )
        page = await context.new_page()
        
        print("Opening Hexagon HTML...")
        await page.goto(html_path)
        
        print(f"Recording for {duration_sec} seconds...")
        await asyncio.sleep(duration_sec)
        
        video_path = await page.video.path()
        await context.close()
        await browser.close()
        
        # Rename standard output to our expected filename
        os.rename(video_path, output_path)
        print(f"Recording saved at: {output_path}")
        return output_path

if __name__ == "__main__":
    asyncio.run(record_html_bg())
