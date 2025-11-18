# NGN Chatbot Knowledge Base - User Guide

## What is This?

This is a **comprehensive, structured dataset** containing all the information about NGN / Neguinho Motors needed to build and train a chatbot. It's designed to work with:

- **LLM Training** - Train language models to understand and respond about NGN Motors
- **RAG (Retrieval Augmented Generation)** - Use as a knowledge base for AI systems that retrieve information to answer questions
- **Chatbot Development** - Direct integration into chatbot platforms
- **Data Analysis** - Structured business information for reporting

## File Structure

The main file is: `ngn_chatbot_knowledge_base.json`

This is a JSON (JavaScript Object Notation) file - a standard format that works with most programming languages and AI tools.

## What's Inside?

### 1. **Company Information** (`company`)
Basic details: name, address, phone, email, what they do

### 2. **Branches** (`branches`)
All three locations (Catford, Tooting, Sutton) with addresses, phones, opening hours

### 3. **Services** (`services`)
Detailed information about:
- Rentals (prices, terms, requirements)
- Sales (new & used bikes, prices, warranties)
- Servicing (types, what's included, prices)
- MOT testing
- Delivery & transport
- Finance options
- Accessories shop
- Accident management

### 4. **Loyalty Programme** (`loyalty_programme`)
NGN Club details: benefits, credits, expiry rules

### 5. **Policies** (`policies`)
Warranty, returns, cancellations, complaints procedures

### 6. **Customer Questions** (`customer_questions`)
200+ real questions customers might ask, organised by category

### 7. **FAQ Intents** (`faq_intents`)
Pre-mapped questions and answers for Finance and Rental agreements

### 8. **Fallback Strategy** (`fallback_strategy`)
What the chatbot should say when it doesn't know an answer - how to redirect to human support

## How to Use This Data

### For LLM Training

1. **Extract the FAQ sections**: Use `faq_intents` and `customer_questions` to train your model
2. **Format as training pairs**: Each question needs a corresponding answer
3. **Use the structure**: The intent categories help organise training data

Example:
```json
{
  "question": "How much to rent a Honda PCX?",
  "answer": "Honda PCX 125 rental starts from £75 per week, with a minimum 6-week hire period. All rentals include TAX, MOT, and weekly maintenance. For exact availability, please contact us on 0208 314 1498."
}
```

### For RAG (Retrieval Augmented Generation)

1. **Chunk the data**: Break the JSON into smaller sections (each service, each branch, etc.)
2. **Create embeddings**: Convert text to vectors for similarity search
3. **Store in vector database**: Use tools like Pinecone, Weaviate, or Chroma
4. **Retrieve on query**: When user asks a question, find relevant chunks and generate answer

Example workflow:
- User asks: "What are your opening hours?"
- System searches for "opening_hours" in branches
- Retrieves: `"monday": "09:00-18:00"` etc.
- Generates answer: "We're open Monday to Saturday, 9am to 6pm..."

### For Chatbot Integration

1. **Direct JSON import**: Many chatbot platforms (Dialogflow, Rasa, Botpress) accept JSON
2. **Convert to platform format**: Transform to the specific format your chatbot needs
3. **Use intents**: Map `faq_intents` to your chatbot's intent system
4. **Implement fallbacks**: Use `fallback_strategy` for when bot can't answer

### For Data Analysis

1. **Extract specific sections**: Pull out services, prices, policies
2. **Create reports**: Analyse what services are offered, pricing structure
3. **Track completeness**: See what information is missing (marked as "contact for details")

## Important Notes

### Missing Data

Many fields say **"contact for details"** - this means:
- The information wasn't on the website
- It needs to be filled in by interviewing the business
- The chatbot should redirect these questions to human support

### Prices

Prices shown are **examples** from the website. Actual prices may vary:
- Check with the business for current pricing
- Update the JSON when you get confirmed prices
- The chatbot should say "from £X" or redirect for exact quotes

### Keeping It Updated

1. **Regular updates**: Business information changes (prices, hours, stock)
2. **Version control**: The `metadata.version` field tracks changes
3. **Add new data**: When you learn new information, add it to the JSON

## Extending the Dataset

### Adding New Services

```json
"services": {
  "new_service_name": {
    "description": "...",
    "price": "...",
    "availability": "..."
  }
}
```

### Adding New Customer Questions

```json
"customer_questions": {
  "categories": {
    "new_category": [
      "Question 1?",
      "Question 2?"
    ]
  }
}
```

### Updating Prices

Find the relevant section and update:
```json
"weekly_prices": {
  "Honda PCX 125": 80,  // Updated from 75
  ...
}
```

## Technical Details

### JSON Format
- **Valid JSON**: Can be parsed by any JSON parser
- **UTF-8 encoding**: Supports all characters (including £, é, etc.)
- **Hierarchical structure**: Organised by business domain

### File Size
- Current size: ~50KB
- Designed to be easily readable and editable
- Can be compressed for storage if needed

### Compatibility
Works with:
- Python (`json` module)
- JavaScript/Node.js (`JSON.parse()`)
- Any programming language with JSON support
- Text editors (for manual editing)
- AI/ML frameworks (LangChain, LlamaIndex, etc.)

## Next Steps

1. **Review the data**: Check what's complete and what needs filling in
2. **Interview the business**: Use the interview questionnaire structure to gather missing info
3. **Update the JSON**: Fill in "contact for details" fields
4. **Test with your chatbot**: Import and see how it performs
5. **Iterate**: Add more questions/answers based on real customer interactions

## Questions?

If you're unsure about:
- **How to use this with your specific chatbot platform**: Check that platform's documentation for JSON import
- **What data is missing**: Look for "contact for details" - these need business input
- **How to structure for RAG**: Break into chunks of 200-500 words, maintain context
- **Training an LLM**: Use the FAQ intents and customer questions as training pairs

## Version History

- **v1.0.0** (2025-01-27): Initial comprehensive dataset created from website scraping, contracts, and documentation

