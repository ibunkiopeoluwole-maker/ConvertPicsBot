import os
import io
import logging
from datetime import datetime
from typing import Dict, Any

from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ==================== CONFIGURATION ====================

# Get bot token from environment variable
TOKEN = os.environ.get("TOKEN") or os.environ.get("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ No TOKEN found! Please set TOKEN environment variable.")

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ==================== CONSTANTS ====================

SUPPORTED_FORMATS = {
    "jpg": {"name": "JPEG", "extension": "jpg"},
    "jpeg": {"name": "JPEG", "extension": "jpg"},
    "png": {"name": "PNG", "extension": "png"},
    "webp": {"name": "WEBP", "extension": "webp"},
    "gif": {"name": "GIF", "extension": "gif"},
    "bmp": {"name": "BMP", "extension": "bmp"},
    "ico": {"name": "ICO", "extension": "ico"},
    "tiff": {"name": "TIFF", "extension": "tiff"},
    "pdf": {"name": "PDF", "extension": "pdf"},
}

MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB
USER_DATA: Dict[int, Dict[str, Any]] = {}

# ==================== HELPER FUNCTIONS ====================

def get_image_format(image_bytes: bytes) -> str:
    """Detect image format from bytes."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        return img.format.lower() if img.format else "unknown"
    except Exception:
        return "unknown"

async def convert_image(image_bytes: bytes, target_format: str) -> bytes:
    """
    Convert image to target format.
    
    Args:
        image_bytes: Raw image data
        target_format: Target format (jpg, png, webp, etc.)
    
    Returns:
        Converted image bytes
    """
    # Open image
    img = Image.open(io.BytesIO(image_bytes))
    
    # Convert RGBA to RGB for JPEG (remove alpha channel)
    if target_format.lower() in ["jpg", "jpeg"]:
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode not in ["RGB", "L"]:
            img = img.convert("RGB")
    
    # Handle ICO format (requires specific sizes)
    if target_format.lower() == "ico":
        output = io.BytesIO()
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)]
        img.save(output, format="ICO", sizes=sizes)
        return output.getvalue()
    
    # Handle PDF conversion
    if target_format.lower() == "pdf":
        output = io.BytesIO()
        img.save(output, format="PDF", resolution=100.0)
        return output.getvalue()
    
    # Regular image conversion
    output = io.BytesIO()
    format_name = target_format.upper()
    
    # Optimize save parameters
    save_kwargs = {}
    if target_format.lower() in ["jpg", "jpeg"]:
        save_kwargs = {"quality": 92, "optimize": True, "progressive": True}
    elif target_format.lower() == "png":
        save_kwargs = {"optimize": True, "compress_level": 6}
    elif target_format.lower() == "webp":
        save_kwargs = {"quality": 90, "lossless": False}
    elif target_format.lower() == "gif":
        save_kwargs = {"optimize": True}
    elif target_format.lower() == "tiff":
        save_kwargs = {"compression": "tiff_lzw"}
    
    img.save(output, format=format_name, **save_kwargs)
    return output.getvalue()

# ==================== BOT COMMANDS ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    welcome_text = f"""
👋 **Hello {user.first_name}!**

Welcome to **ConvertPicsBot** - Your Image Conversion Assistant! 🎨

📸 **How to use:**
1. Send me any image
2. Choose your desired format from the buttons below
3. I'll convert and send it back instantly!

🔄 **Supported Formats:**
• JPG / JPEG
• PNG
• WEBP
• GIF
• BMP
• ICO (Icon)
• TIFF
• PDF

📝 **Commands:**
/start - Show this message
/help - Get detailed help
/about - About this bot

Let's get started! Send me an image now. 🚀
"""
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = """
📖 **Help Guide - ConvertPicsBot**

🔹 **How it works:**
1. Send an image to the chat
2. Choose a format from the inline buttons
3. Wait for conversion
4. Download your converted file

🎯 **Supported Formats:**
• **Images:** JPG, PNG, WEBP, GIF, BMP, ICO, TIFF
• **Documents:** PDF

⚡ **Tips:**
• Maximum file size: 20MB
• Batch conversion: Send multiple images one by one
• Original quality is preserved
• Transparent backgrounds are handled automatically

❓ **Need help?**
Just send an image and follow the prompts!

🔗 **Commands:**
/start - Welcome message
/help - This help guide
/about - Bot information
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /about command."""
    about_text = """
🤖 **ConvertPicsBot v1.0**

📸 **The Ultimate Image Converter Bot**

✨ **Features:**
• Convert between 8+ formats
• Inline format selection
• High-quality output
• Optimized file sizes
• Handles transparent backgrounds
• Converts to PDF too!

🛠️ **Built with:**
• Python 3.11+
• python-telegram-bot
• Pillow (PIL)

🚀 **Hosted on:** Railway

📅 **Created:** 2024

👨‍💻 **Open Source**
Contributions welcome on GitHub!

📢 **Send /start to begin!**
"""
    await update.message.reply_text(about_text, parse_mode="Markdown")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel command to clear user data."""
    user_id = update.effective_user.id
    if user_id in USER_DATA:
        del USER_DATA[user_id]
        await update.message.reply_text("✅ Conversion cancelled. Send a new image to start over.")
    else:
        await update.message.reply_text("ℹ️ No active conversion to cancel.")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown commands."""
    await update.message.reply_text(
        "❌ Unknown command. Use /start, /help, or /about.\n"
        "Or just send me an image to convert!"
    )

# ==================== IMAGE HANDLER ====================

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming images."""
    user_id = update.effective_user.id
    
    # Get the largest photo
    photo = update.message.photo[-1]
    file = await photo.get_file()
    
    # Check file size
    if file.file_size > MAX_IMAGE_SIZE:
        await update.message.reply_text(
            f"❌ Image too large! ({file.file_size // 1024 // 1024}MB)\n"
            f"Maximum allowed: {MAX_IMAGE_SIZE // 1024 // 1024}MB\n"
            "Please send a smaller image."
        )
        return
    
    # Download image
    try:
        image_bytes = await file.download_as_bytearray()
        image_bytes = bytes(image_bytes)
    except Exception as e:
        logger.error(f"Failed to download image: {e}")
        await update.message.reply_text(
            "❌ Failed to download image. Please try again."
        )
        return
    
    # Detect original format
    original_format = get_image_format(image_bytes)
    
    # Store in user data
    USER_DATA[user_id] = {
        "image_bytes": image_bytes,
        "original_format": original_format,
        "timestamp": datetime.now()
    }
    
    # Create inline keyboard
    keyboard = [
        [InlineKeyboardButton("🖼️ JPG", callback_data="jpg"),
         InlineKeyboardButton("🖼️ PNG", callback_data="png")],
        [InlineKeyboardButton("🖼️ WEBP", callback_data="webp"),
         InlineKeyboardButton("🖼️ GIF", callback_data="gif")],
        [InlineKeyboardButton("🖼️ BMP", callback_data="bmp"),
         InlineKeyboardButton("🖼️ ICO", callback_data="ico")],
        [InlineKeyboardButton("🖼️ TIFF", callback_data="tiff"),
         InlineKeyboardButton("📄 PDF", callback_data="pdf")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send format selection
    original_display = original_format.upper() if original_format != "unknown" else "Unknown"
    await update.message.reply_text(
        f"🔄 **Choose conversion format**\n\n"
        f"📂 Original: `{original_display}`\n"
        f"📏 Size: {len(image_bytes) // 1024}KB\n\n"
        f"Select your desired format:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# ==================== CALLBACK HANDLER ====================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    selected_format = query.data
    
    # Handle cancel
    if selected_format == "cancel":
        if user_id in USER_DATA:
            del USER_DATA[user_id]
        await query.edit_message_text(
            "❌ **Conversion cancelled.**\n\nSend a new image to start over.",
            parse_mode="Markdown"
        )
        return
    
    # Check if user has stored image
    if user_id not in USER_DATA:
        await query.edit_message_text(
            "⚠️ **No image found!**\n\n"
            "Please send an image first, then choose a format.",
            parse_mode="Markdown"
        )
        return
    
    # Get user data
    user_info = USER_DATA[user_id]
    image_bytes = user_info["image_bytes"]
    original_format = user_info.get("original_format", "unknown")
    
    # Update message to show processing
    await query.edit_message_text(
        f"🔄 **Converting to {selected_format.upper()}...**\n\n"
        f"⏳ Please wait, this may take a moment.",
        parse_mode="Markdown"
    )
    
    try:
        # Convert image
        converted_bytes = await convert_image(image_bytes, selected_format)
        
        # Prepare filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = SUPPORTED_FORMATS.get(selected_format, {}).get("extension", selected_format)
        filename = f"converted_{timestamp}.{extension}"
        
        # Send converted file
        caption = (
            f"✅ **Conversion Complete!**\n\n"
            f"📂 Original: `{original_format.upper()}`\n"
            f"📂 New: `{selected_format.upper()}`\n"
            f"📏 Size: {len(converted_bytes) // 1024}KB\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Send as document for better handling
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=io.BytesIO(converted_bytes),
            filename=filename,
            caption=caption,
            parse_mode="Markdown"
        )
        
        # Clean up user data
        del USER_DATA[user_id]
        
    except Exception as e:
        logger.error(f"Conversion error: {str(e)}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"❌ **Conversion Failed!**\n\n"
                f"Error: `{str(e)}`\n\n"
                f"Please try again with a different format or image."
            ),
            parse_mode="Markdown"
        )

# ==================== ERROR HANDLER ====================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    logger.error(f"Update {update} caused error: {context.error}")
    
    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "❌ **An error occurred!**\n\n"
                "Please try again later or contact the bot administrator.\n"
                "If the issue persists, send /cancel and try again."
            ),
            parse_mode="Markdown"
        )

# ==================== MAIN FUNCTION ====================

def main() -> None:
    """Start the bot."""
    logger.info("🚀 Starting ConvertPicsBot...")
    
    # Build application
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    
    # Add callback handler
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start bot
    logger.info("✅ Bot is running and listening for messages...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
