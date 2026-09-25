import os
from io import BytesIO
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, MessageHandler, CommandHandler,
    ContextTypes, filters
)
from PIL import Image

BOT_TOKEN = os.environ.get("BOT_TOKEN")  # set this in your environment/secrets
COLLAGE_SIZE = 4  # number of photos before auto-making a collage

# Temporary in-memory storage: {user_id: [image_bytes, ...]}
user_photos = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Send me photos and I'll turn them into a collage after {COLLAGE_SIZE}. "
        "Or send /collage anytime to build one from what you've sent so far."
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()

    user_photos.setdefault(user_id, []).append(bytes(photo_bytes))

    count = len(user_photos[user_id])
    await update.message.reply_text(f"Got it ({count}/{COLLAGE_SIZE}).")

    if count >= COLLAGE_SIZE:
        await make_and_send_collage(update, context, user_id)

async def collage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_photos.get(user_id):
        await update.message.reply_text("Send me some photos first!")
        return
    await make_and_send_collage(update, context, user_id)

async def make_and_send_collage(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    images = [Image.open(BytesIO(b)).convert("RGB") for b in user_photos[user_id]]
    collage = build_grid_collage(images)

    buffer = BytesIO()
    buffer.name = "collage.jpg"
    collage.save(buffer, "JPEG", quality=95)
    buffer.seek(0)

    await update.message.reply_photo(photo=buffer, caption="Here's your collage!")
    user_photos[user_id] = []  # reset after sending

def build_grid_collage(images, tile_size=600):
    """Arrange images into a roughly square grid, cropped to fill each tile."""
    n = len(images)
    cols = int(n ** 0.5)
    if cols * cols < n:
        cols += 1
    rows = -(-n // cols)  # ceil division

    canvas = Image.new("RGB", (cols * tile_size, rows * tile_size), "white")

    for i, img in enumerate(images):
        img = crop_to_square(img).resize((tile_size, tile_size))
        x = (i % cols) * tile_size
        y = (i // cols) * tile_size
        canvas.paste(img, (x, y))

    return canvas

def crop_to_square(img):
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("collage", collage_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == "__main__":
    main()
