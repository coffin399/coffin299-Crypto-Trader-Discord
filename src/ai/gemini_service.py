import google.generativeai as genai
import json
from ..logger import setup_logger

logger = setup_logger("gemini_service")

class GeminiService:
    def __init__(self, api_key, model_name="gemini-2.0-flash-exp", system_prompt=""):
        self.api_key = api_key
        self.model_name = model_name
        self.system_prompt = system_prompt
        
        if not api_key:
            logger.warning("Gemini API Key is missing!")
        else:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=self.system_prompt
            )

    async def analyze_market(self, market_data_summary):
        """
        Sends market data to Gemini and gets a trading decision.
        """
        if not self.api_key:
            return {"action": "HOLD", "reasoning": "No API Key"}

        prompt = f"""
        Analyze the following market data and provide a trading decision.
        
        Market Data:
        {market_data_summary}
        
        Respond strictly in JSON format:
        {{
            "action": "BUY" | "SELL" | "HOLD",
            "pair": "Target Pair (e.g. BTC/USDC)",
            "confidence": 0.0 to 1.0,
            "reasoning": "Brief explanation"
        }}
        """
        
        try:
            # Note: generate_content is synchronous in the current SDK, 
            # but we can wrap it or run it in an executor if needed. 
            # For now, we'll run it directly as it's usually fast enough or we accept the block.
            # Ideally use async_generate_content if available in the version.
            response = await self.model.generate_content_async(prompt)
            text = response.text
            
            # Clean up markdown code blocks if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
                
            decision = json.loads(text.strip())
            logger.info(f"Gemini Decision: {decision}")
            return decision
            
        except Exception as e:
            logger.error(f"Gemini Analysis Failed: {e}")
            return {"action": "HOLD", "reasoning": f"Error: {e}"}
