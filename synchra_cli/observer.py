import asyncio
import logging
from typing import Optional, List
from uuid import UUID

from synchra import SynchraClient
from synchra_cli.formatter import Formatter

class SynchraObserver:
    """The main logic for the Synchra CLI Observer."""
    
    def __init__(self, client: SynchraClient):
        self.client = client
        self.channel_id: Optional[UUID] = None
        self.channel_providers: List[dict] = []
        self.user_provider_id: Optional[UUID] = None

    async def setup(self, channel_id: Optional[UUID] = None, provider: Optional[str] = None, name: Optional[str] = None):
        """Find the channel and setup the observer."""
        # 1. Fetch User Profile Info
        try:
            user_info = await self.client.user.get_info()
            user_providers = await self.client.user.list_providers()
            
            p_list = ", ".join([p.get('provider', 'unknown').upper() for p in user_providers])
            Formatter.profile("Authenticated User", {
                "username": user_info.get("username", "Unknown"),
                "user_id": user_info.get("id", "Unknown"),
                "platforms": p_list
            })
            
            if user_providers:
                # Picker for default sender
                self.user_provider_id = UUID(user_providers[0]['id'])
            else:
                Formatter.error("No linked providers found for your account. Chat is disabled.")
        except Exception as e:
            Formatter.error(f"Failed to fetch user profile: {e}")

        # 2. Resolve Target Channel
        if channel_id:
            self.channel_id = channel_id
        elif provider and name:
            Formatter.info(f"Resolving channel: {provider}/{name}...")
            channels = await self.client.channels.list(
                provider=provider.lower(), 
                provider_channel_name=name
            )
            if channels:
                self.channel_id = channels[0].id
            else:
                raise Exception(f"No channel found for {provider}/{name}")
        else:
            raise Exception("No channel ID or provider/name provided.")
        
        if not self.channel_id:
            raise Exception("No channel ID provided and could not resolve one from target username.")

        # 3. Fetch Channel Details & Providers
        self.channel_providers = await self.client.channels.list_providers(self.channel_id)
        
        target_platforms = ", ".join([
            getattr(p.provider, 'value', str(p.provider)).upper() 
            for p in self.channel_providers
        ])
        Formatter.profile("Target", {
            "channel_id": self.channel_id,
            "platforms": target_platforms,
        })

        # 4. Setup WebSocket handlers
        @self.client.ws.on("chat_message")
        async def on_chat(event):
            data = event.get('data', {})
            provider = data.get('provider', event.get('provider', 'unknown'))
            if hasattr(provider, 'value'):
                provider = provider.value
                
            parts = data.get('message_parts', [])
            message = "".join([p.get('text', '') for p in parts]) or data.get('message', '')

            Formatter.chat(
                provider,
                data.get('viewer_display_name', 'System'),
                message
            )

        @self.client.ws.on("activity")
        async def on_activity(event):
            data = event.get('data', {})
            provider = data.get('provider', event.get('provider', 'synchra'))
            if hasattr(provider, 'value'):
                provider = provider.value
                
            action = event.get('action', 'triggered')
            activity_type = data.get('type', 'event')
            viewer = data.get('viewer_display_name', 'Someone')
            
            Formatter.activity(
                provider,
                activity_type,
                f"{viewer} {action} {activity_type}"
            )

        await self.client.connect()
        await self.client.ws.subscribe("chat_message", self.channel_id)
        await self.client.ws.subscribe("activity", self.channel_id)
        
        Formatter.info("Successfully connected to events. Type your messages below!")

    async def send_broadcast(self, message: str):
        """Send a message to all platforms using the SDK broadcast helper."""
        if not self.user_provider_id:
            Formatter.error("Cannot send: No user provider available.")
            return

        try:
            result = await self.client.chat.send_message_all(
                channel_id=self.channel_id,
                message=message,
                user_provider_id=self.user_provider_id,
                providers=self.channel_providers
            )
            
            success = result.get("success", 0)
            failed = result.get("failed", 0)
            
            if success > 0:
                Formatter.info(f"Broadcasted message to {success} platforms.")
            if failed > 0:
                for err in result.get("errors", []):
                    p_name = getattr(err['platform'], 'value', str(err['platform']))
                    Formatter.error(f"Failed to send to {p_name.upper()}: {err['error']}")
        except Exception as e:
            Formatter.error(f"Broadcast failed: {e}")
