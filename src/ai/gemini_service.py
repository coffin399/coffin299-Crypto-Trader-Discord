import google.generativeai as genai
import json
import itertools
from ..logger import setup_logger

logger = setup_logger("gemini_service")

class GeminiService:
    def __init__(self, api_keys, model_name="gemini-2.0-flash-exp", system_prompt=""):
        # Handle single key string or list of keys
        if isinstance(api_keys, str):
            self.api_keys = [api_keys]
        else:
            self.api_keys = api_keys
            
        self.key_cycle = itertools.cycle(self.api_keys)
        self.current_key = next(self.key_cycle) if self.api_keys else None
        
        self.model_name = model_name
        self.system_prompt = system_prompt
        
        if not self.api_keys:
            logger.warning("Gemini API Keys are missing!")
        else:
            self._configure_client()

    def _configure_client(self):
        """Configures the GenAI client with the current key."""
        logger.info(f"Switching to Gemini API Key: ...{self.current_key[-4:] if self.current_key else 'None'}")
        genai.configure(api_key=self.current_key)
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=self.system_prompt
        )

    def rotate_key(self):
        """Rotates to the next API key in the list."""
        if not self.api_keys: return
        self.current_key = next(self.key_cycle)
        self._configure_client()

    async def analyze_market(self, market_data_summary):
        """
        Sends market data to Gemini and gets a trading decision.
        """
        if not self.current_key:
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
        
        # Try current key, if fail, rotate and retry once
        max_retries = len(self.api_keys)
        attempts = 0
        
        while attempts < max_retries:
            try:
                # Always rotate key BEFORE request to distribute load (Round Robin)
                # Or rotate only on failure? User said "Key A -> Key B", implies round robin usage or sequential.
                # "Key A used, next Key B". Let's rotate AFTER a successful use or BEFORE?
                # Usually rotation is for rate limits. Let's rotate for every request to be safe/fair.
                self.rotate_key() 
                
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
                logger.error(f"Gemini Analysis Failed with key ...{self.current_key[-4:]}: {e}")
                attempts += 1
                # Key rotation happens at start of loop, so next iter will use next key
        
        return {"action": "HOLD", "reasoning": "All API keys failed."}
