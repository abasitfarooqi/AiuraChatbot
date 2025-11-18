# Chatbot Service Configuration Guide

The chatbot service is now **fully configurable** via JSON files and the admin panel. All hardcoded values have been moved to `config/chatbot_service_config.json`.

## Configuration File

**Location:** `config/chatbot_service_config.json`

## Configurable Settings

### 1. Greetings (`greetings`)

Controls how the chatbot handles greetings and initial interactions.

- **`simple_greetings`**: List of greeting phrases that trigger special handling
  - Default: `["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings"]`
  - **Reason**: Identifies when user is just saying hello vs asking a question

- **`initial_suggestions`**: Suggestions shown on first message or greeting
  - Default: `["What services do you offer?", "Tell me about rental bikes", "What are your opening hours?", "Where are your branches located?"]`
  - **Reason**: Provides helpful starting points for new users

### 2. Topic Detection (`topic_detection`)

Controls how the chatbot identifies topics in user messages.

- **`topic_keywords`**: Maps topics to keyword lists for detection
  - Example: `{"rental": ["rental", "rent", "hire"], "sale": ["sale", "buy"]}`
  - **Reason**: Allows customisation of how topics are detected based on business terminology

- **`service_topics`**: List of service-related topics
  - Default: `["rental", "sale", "finance", "servicing", "mot", "delivery", "accessories", "accident"]`
  - **Reason**: Defines which topics are considered "services" for cross-selling logic

### 3. Question Analysis (`question_analysis`)

Controls how the chatbot determines if a question is complete.

- **`complete_question_indicators`**: Patterns that indicate a complete question
  - Format: `[{"indicator": "what", "keywords": ["service", "price"]}, ...]`
  - **Reason**: Allows fine-tuning of when to use conversation context vs standalone question

- **`min_words_for_complete`**: Minimum words for a complete question (default: 4)
  - **Reason**: Prevents treating very short messages as complete questions

- **`min_words_for_question_structure`**: Minimum words for question structure detection (default: 5)
  - **Reason**: Ensures enough context for question word detection

- **`max_short_question_words`**: Maximum words considered "short" (default: 2)
  - **Reason**: Identifies ambiguous/incomplete questions

### 4. Suggestions (`suggestions`)

Controls the suggestion system that helps guide users.

- **`service_suggestions`**: Service-specific suggestion templates
  - Each service has:
    - `primary`: List of primary suggestions for that service
    - `cross_sell`: Cross-selling message when user focuses on one service
  - **Reason**: Allows customisation of suggestions per service type

- **`all_services`**: Map of all services to suggestion text
  - **Reason**: Used for cross-selling when user explores multiple services

- **`default_suggestions`**: Fallback suggestions when no specific match
  - **Reason**: Ensures users always get helpful suggestions

- **`max_suggestions`**: Maximum number of suggestions to show (default: 5)
  - **Reason**: Controls UI clutter

- **`min_services_for_cross_sell`**: Minimum services asked about before cross-selling (default: 2)
  - **Reason**: Prevents premature cross-selling

- **`min_messages_for_cross_sell`**: Minimum messages before cross-selling (default: 3)
  - **Reason**: Ensures user has engaged before suggesting other services

- **`multi_service_message`**: Message shown when suggesting other services
  - **Reason**: Customisable cross-selling message

### 5. Intelligent Suggestions (`intelligent_suggestions`)

Advanced suggestion logic based on conversation patterns.

- **`enabled`**: Enable/disable intelligent suggestions (default: true)
  - **Reason**: Allows disabling if not needed

- **`min_questions_for_analysis`**: Minimum questions before analysis (default: 4)
  - **Reason**: Ensures enough conversation history for pattern detection

- **`rental_follow_ups`**: Follow-up suggestions for rental questions
  - Keys: `deposit`, `insurance`, `delivery`
  - **Reason**: Suggests related rental questions based on conversation

- **`sale_follow_ups`**: Follow-up suggestions for sale questions
  - Keys: `finance`, `test_ride`, `warranty`
  - **Reason**: Suggests related sale questions

- **`finance_follow_ups`**: Follow-up suggestions for finance questions
  - Keys: `interest_rate`, `term`, `deposit`
  - **Reason**: Suggests related finance questions

- **`servicing_follow_ups`**: Follow-up suggestions for servicing questions
  - Keys: `cost`, `collect`, `mot`
  - **Reason**: Suggests related servicing questions

- **`multi_service_follow_ups`**: Follow-ups when user asks about multiple services
  - Keys: `delivery`, `accessories`, `accident`
  - **Reason**: Suggests complementary services

### 6. Response Formatting (`response_formatting`)

Controls how responses are formatted and what information is added.

- **`add_contact_info`**: Whether to add contact info to responses (default: true)
  - **Reason**: Can disable if contact info is already in knowledge base

- **`contact_keywords`**: Keywords that trigger contact info addition
  - Default: `["service", "rental", "sale", "finance", "opening", "branch", "contact", "help"]`
  - **Reason**: Only adds contact info for relevant queries

- **`min_response_length_for_contact`**: Minimum response length before adding contact (default: 50)
  - **Reason**: Prevents adding contact to very short responses

- **`contact_info`**: Contact information text to append
  - Default: `"Contact: 0208 314 1498 or enquiries@neguinhomotors.co.uk"`
  - **Reason**: Customisable contact information

- **`default_empty_response`**: Response when chatbot has nothing to say
  - Default: `"I'm here to help! How can I assist you today?"`
  - **Reason**: Friendly fallback message

### 7. Context Management (`context_management`)

Controls how conversation history is used.

- **`max_context_messages`**: Maximum messages to include in LLM context (default: 10)
  - **Reason**: Controls token usage and context window size

- **`max_recent_messages_for_query`**: Maximum recent messages for query building (default: 6)
  - **Reason**: Limits how much history is used for RAG query enhancement

- **`max_user_messages_for_context`**: Maximum user messages for context building (default: 4)
  - **Reason**: Controls context window for incomplete questions

### 8. Validation (`validation`)

Controls response validation to prevent hallucinations.

- **`enable_response_validation`**: Enable/disable validation (default: true)
  - **Reason**: Can disable if validation is too strict

- **`fallback_message`**: Message when validation fails
  - **Reason**: Safe fallback when response might contain hallucinations

## Admin Panel Access

1. Go to **Admin Panel** → **Chatbot Service** tab
2. Click **"Load Config"** to view current settings
3. Edit JSON directly
4. Click **"Validate JSON"** to check syntax
5. Click **"Save Config"** to save changes

**Note:** Server restart recommended for full effect, though some changes apply on next request.

## API Endpoints

- `GET /api/v1/config/chatbot-service` - Get current config
- `POST /api/v1/config/chatbot-service` - Update config

## Example: Customising Suggestions

To change rental suggestions:

```json
{
  "suggestions": {
    "service_suggestions": {
      "rental": {
        "primary": [
          "What bikes can I rent?",
          "How much does rental cost?",
          "What's the minimum rental period?"
        ],
        "cross_sell": "We also offer bike sales - interested?"
      }
    }
  }
}
```

## Example: Adjusting Context Window

To use more conversation history:

```json
{
  "context_management": {
    "max_context_messages": 15,
    "max_recent_messages_for_query": 8,
    "max_user_messages_for_context": 6
  }
}
```

## Example: Disabling Contact Info

To stop adding contact info automatically:

```json
{
  "response_formatting": {
    "add_contact_info": false
  }
}
```

## Benefits

1. **No Code Changes**: All settings editable via admin panel
2. **Offline Ready**: All config stored in JSON files
3. **Easy Testing**: Change settings and test immediately
4. **Business Control**: Non-technical users can adjust behaviour
5. **Version Control**: Config files can be versioned
6. **A/B Testing**: Easy to test different configurations

## Best Practices

1. **Backup Before Changes**: Always backup config files
2. **Validate JSON**: Use "Validate JSON" button before saving
3. **Test Changes**: Test chatbot after configuration changes
4. **Document Changes**: Keep notes on what you changed and why
5. **Incremental Changes**: Make small changes and test, not large changes at once

## Troubleshooting

### Suggestions Not Showing

- Check `max_suggestions` is > 0
- Verify `service_suggestions` has entries for detected topics
- Check `min_services_for_cross_sell` and `min_messages_for_cross_sell` thresholds

### Context Not Working

- Check `max_context_messages` is sufficient
- Verify `max_recent_messages_for_query` is appropriate
- Ensure conversation has enough history

### Contact Info Not Appearing

- Check `add_contact_info` is `true`
- Verify query contains keywords from `contact_keywords`
- Check response length exceeds `min_response_length_for_contact`

### Topics Not Detected

- Add more keywords to `topic_keywords` for your business terminology
- Check keywords match how customers actually ask questions
- Consider synonyms and variations

