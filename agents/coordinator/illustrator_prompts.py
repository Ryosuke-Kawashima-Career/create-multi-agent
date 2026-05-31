IMAGE_PROMPT_FORMAT = """
{
  "task": "generate_image",
  "image_type": "travel_itinerary_cover",
  "canvas": {
    "aspect_ratio": "9:16",
  },
  "text_elements": [
    {
      "text": "旅程タイトル",
      "position": "center-left",
      "font_style": <the_most_appropriate_font_for_each_text_element>,
      "size": "very large",
      "color": "white",
    }
  ],
  "visual_elements": [
    {
      "subject": "main travel scene",
      "position": "right side",
      "style": "clean commercial illustration"
    }
  ]
}
"""