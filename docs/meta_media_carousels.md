Interactive media carousel messages
Updated: Dec 22, 2025
Interactive media carousel messages display a set of horizontally scrollable media cards. Each card can display an image or video header, body text, and either quick-reply buttons or a URL button.
For example, this is an interactive media card carousel message showing three cards in a scrollable area (highlighted by a dotted rectangle), each with an image header, body text, and URL button:

This is the same message, but using quick-reply buttons instead of URL buttons:

Components
Messages must include between 2 and 10 cards.
Main message body text is required.
Main message headers, footers, and interactive components are not supported.
Cards must include either an image or video header. Other header types are not supported.
Card body text is optional.
Cards must include either one URL button, or one or more quick-reply buttons. Button types and numbers must match across all cards (for example, if you define a card with 2 quick-reply buttons, all cards must define exactly 2 quick-reply buttons).
Request syntax
curl 'https://graph.facebook.com/<API_VERSION>/<BUSINESS_PHONE_NUMBER_ID>/messages' \
-H 'Content-Type: application/json' \
-H 'Authorization: Bearer <ACCESS_TOKEN>' \
-d '
{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "<USER_PHONE_NUMBER>",
  "type": "interactive",
  "interactive": {
    "type": "carousel",
    "body": {
      "text": "<MESSAGE_BODY_TEXT>"
    },
    "action": {

      <!-- First card object -->
      "cards": [
        {
          "card_index": <CARD_INDEX>,
          "type": "cta_url",
          "header": {
            "type": "<HEADER_TYPE>",
            "<HEADER_TYPE>": {
              "link": "<MEDIA_ASSET_URL>"
            }
          },

          <!-- Card body text is optional -->
          "body": {
            "text": "<CARD_BODY_TEXT>"
          },

          "action": {
            <!-- Only if using a URL button -->
            "name": "cta_url",
            "parameters": {
              "display_text": "<URL_BUTTON_LABEL>",
              "url": "<URL_BUTTON_URL>"
            }
            <!-- Only if using one or more quick-reply buttons -->
            "buttons": [
              {
                "type": "quick_reply",
                "quick_reply": {
                  "id": "<QUICK_REPLY_BUTTON_ID>",
                  "title": "<QUICK_REPLY_BUTTON_LABEL>"
                }
              },
              <!-- Additional quick-reply buttons would follow -->
          }
        },
        <!-- Additional card objects would follow -->
      ]
    }
  }
}'
Request parameters
Placeholder	Description	Example value
<ACCESS_TOKEN>

String
Required.

Access token.
EAAJB...
<API_VERSION>

String
Optional.

API version.
v23.0
<BUSINESS_PHONE_NUMBER_ID>

Integer
Required.

Business phone number ID.
106540352242922
<CARD_BODY_TEXT>

String
Optional.

Card body text. Max 160 characters, and up to 2 line breaks.
*Blue Echeveria*\n\nA rosette-shaped succulent with powdery blue leaves, perfect for brightening up any space.
<CARD_INDEX>

Integer
Required.

Zero-index card index. Cards will appear left to right in scrollable view, starting from 0.
0
<HEADER_TYPE>

String
Required.

Header type. Value can be:

image — Indicates a card image header.

video — Indicates a card video header.

See Supported media types.
image
<MEDIA_ASSET_URL>

String
Required.

Publicly available media asset URL.
https://www.luckyshrub.com/assets/blue-echeveria.jpeg
<MESSAGE_BODY_TEXT>

String
Required.

Main message body text. Maximum 1024 characters.
Of course! Here are three of our latest arrivals, each under $25:
<QUICK_REPLY_BUTTON_ID>

String
Required if using a quick-reply button.

Quick-reply button ID. Maximum 256 characters.
learn-blue-echeveria
<QUICK_REPLY_BUTTON_LABEL>

String
Required if using a quick-reply button.

Quick-reply button label text. Maximum 20 characters.
Learn more
<URL_BUTTON_LABEL>

String
Required if using a URL button.

URL button label text. Maximum 20 characters.
Buy now
<URL_BUTTON_URL>

String
Required if using a URL button.

URL to load in the device’s default web browser when tapped by the user.
https://shop.luckyshrub.com/latest/blue-echeveria
<USER_PHONE_NUMBER>

String
Required.

WhatsApp user phone number.
16505551234
Example requests
URL buttons example
This example request sends a media carousel message composed of 3 cards, each with an image header, card body text, and a URL button.
curl 'https://graph.facebook.com/v23.0/106540352242922/messages' \
-H 'Content-Type: application/json' \
-H 'Authorization: Bearer EAAJB...' \
-d '
{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "16505551234",
  "type": "interactive",
  "interactive": {
    "type": "carousel",
    "body": {
      "text": "Of course! Here are three of our latest arrivals, each under $25:"
    },
    "action": {
      "cards": [
        {
          "card_index": 0,
          "type": "cta_url",
          "header": {
            "type": "image",
            "image": {
              "link": "https://www.luckyshrub.com/assets/blue-echeveria.jpeg"
            }
          },
          "body": {
            "text": "*Blue Echeveria*\n\nA rosette-shaped succulent with powdery blue leaves, perfect for brightening up any space."
          },
          "action": {
            "name": "cta_url",
            "parameters": {
              "display_text": "Buy now",
              "url": "https://shop.luckyshrub.com/latest/blue-echeveria"
            }
          }
        },
        {
          "card_index": 1,
          "type": "cta_url",
          "header": {
            "type": "image",
            "image": {
              "link": "https://www.luckyshrub.com/assets/zebra-haworthia.jpeg"
            }
          },
          "body": {
            "text": "*Zebra Haworthia*\n\nStriking white stripes on deep green leaves give this compact succulent a bold, modern look."
          },
          "action": {
            "name": "cta_url",
            "parameters": {
              "display_text": "Buy now",
              "url": "https://shop.luckyshrub.com/latest/zebra-haworthia"
            }
          }
        },
        {
          "card_index": 2,
          "type": "cta_url",
          "header": {
            "type": "image",
            "image": {
              "link": "https://www.luckyshrub.com/assets/panda-plant.jpeg"
            }
          },
          "body": {
            "text": "*Panda Plant*\n\nSoft, fuzzy leaves with chocolate-brown edges—adorable and easy to care for."
          },
          "action": {
            "name": "cta_url",
            "parameters": {
              "display_text": "Buy now",
              "url": "https://shop.luckyshrub.com/latest/panda-plant"
            }
          }
        }
      ]
    }
  }
}'
Quick-reply buttons example
This example request sends a media carousel message composed of 3 cards, each with an image header, card body text, and two quick-reply buttons.
curl 'https://graph.facebook.com/v23.0/106540352242922/messages' \
-H 'Content-Type: application/json' \
-H 'Authorization: Bearer EAAJB...' \
-d '
{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "16505551234",
  "type": "interactive",
  "interactive": {
    "type": "carousel",
    "body": {
      "text": "Of course! Here are three of our latest arrivals, each under $25:"
    },
    "action": {
      "cards": [
        {
          "card_index": 0,
          "type": "cta_url",
          "header": {
            "type": "image",
            "image": {
              "link": "https://www.luckyshrub.com/assets/blue-echeveria.jpeg"
            }
          },
          "body": {
            "text": "*Blue Echeveria*\n\nA rosette-shaped succulent with powdery blue leaves, perfect for brightening up any space."
          },
          "action": {
            "buttons": [
              {
                "type": "quick_reply",
                "quick_reply": {
                  "id": "learn-blue-echeveria",
                  "title": "Learn more"
                }
              },
              {
                "type": "quick_reply",
                "quick_reply": {
                  "id": "fav-blue-echeveria",
                  "title": "Add to favorites"
                }
              }
            ]
          }
        },
        {
          "card_index": 1,
          "type": "cta_url",
          "header": {
            "type": "image",
            "image": {
              "link": "https://www.luckyshrub.com/assets/zebra-haworthia.jpeg"
            }
          },
          "body": {
            "text": "*Zebra Haworthia*\n\nStriking white stripes on deep green leaves give this compact succulent a bold, modern look."
          },
          "action": {
            "buttons": [
              {
                "type": "quick_reply",
                "quick_reply": {
                  "id": "learn-zebra-haworthia",
                  "title": "Learn more"
                }
              },
              {
                "type": "quick_reply",
                "quick_reply": {
                  "id": "fav-zebra-haworthia",
                  "title": "Add to favorites"
                }
              }
            ]
          }
        },
        {
          "card_index": 2,
          "type": "cta_url",
          "header": {
            "type": "image",
            "image": {
              "link": "https://www.luckyshrub.com/assets/panda-plant.jpeg"
            }
          },
          "body": {
            "text": "*Panda Plant*\n\nSoft, fuzzy leaves with chocolate-brown edges—adorable and easy to care for."
          },
          "action": {
            "buttons": [
              {
                "type": "quick_reply",
                "quick_reply": {
                  "id": "learn-panda-plant",
                  "title": "Learn more"
                }
              },
              {
                "type": "quick_reply",
                "quick_reply": {
                  "id": "fav-panda-plant",
                  "title": "Add to favorites"
                }
              }
            ]
          }
        }
      ]
    }
  }
}'
Example response
{
  "messaging_product": "whatsapp",
  "contacts": [
    {
      "input": "+16505551234",
      "wa_id": "16505551234"
    }
  ],
  "messages": [
    {
      "id": "wamid.HBgLMTY0NjcwNDM1OTUVAgARGBI1RjQyNUE3NEYxMzAzMzQ5MkEA"
    }
  ]
}