import asyncio
import logging
from typing import Optional, List
from uuid import UUID

from synchra import SynchraClient
from synchra.models import UserProviderPublic, BroadcastResponse
from synchra_cli.formatter import Formatter

class SynchraObserver:
    """The main logic for the Synchra CLI Observer."""
    
    def __init__(self, client: SynchraClient):
        self.client = client
        self.channel_id: Optional[UUID] = None
        self.channel_providers: List[UserProviderPublic] = []
        self.user_provider_id: Optional[UUID] = None

    async def setup(self, channel_id: Optional[UUID] = None, provider: Optional[str] = None, name: Optional[str] = None):
        """Find the channel and setup the observer."""
        # 1. Fetch User Profile Info
        try:
            user_info = await self.client.user.get_info()
            user_providers = await self.client.user.list_providers()
            
            p_list = ", ".join([p.provider.value.upper() for p in user_providers])
            Formatter.profile("Authenticated User", {
                "username": user_info.username,
                "user_id": str(user_info.id),
                "platforms": p_list
            })
            
            if user_providers:
                # Picker for default sender (could be smarter, but we'll use first for now)
                self.user_provider_id = user_providers[0].id
            else:
                Formatter.error("No linked providers found for your account. Chat is disabled.")
        except Exception as e:
            Formatter.error(f"Failed to fetch user profile: {e}")

        # 2. Resolve Target Channel
        channel_data = None
        if channel_id:
            try:
                channel_data = await self.client.channels.get(channel_id)
                self.channel_id = channel_id
            except Exception as e:
                Formatter.error(f"Failed to fetch channel {channel_id}: {e}")
        elif provider and name:
            Formatter.info(f"Resolving channel: {provider}/{name}...")
            channels = await self.client.channels.list(
                provider=provider.lower(), 
                provider_channel_name=name
            )
            if channels:
                channel_data = channels[0]
                self.channel_id = channels[0].id
            else:
                raise Exception(f"No channel found for {provider}/{name}")
        else:
            raise Exception("No channel ID or provider/name provided.")
        
        if not self.channel_id:
            raise Exception("No channel ID provided and could not resolve one from target username.")

        # 3. Fetch Channel Detail & Providers
        self.channel_providers = await self.client.channels.list_providers(self.channel_id)
        
        # Consolidation for Profile View
        display_name = channel_data.display_name if channel_data else "Unknown"
        target_platforms = ", ".join([p.provider.value.upper() for p in self.channel_providers])
        
        Formatter.profile("Target Monitoring", {
            "name": display_name,
            "id": str(self.channel_id),
            "platforms": target_platforms,
        })

        # 4. Setup WebSocket handlers
        @self.client.ws.on("chat_message")
        async def on_chat(event):
            data = event.get('data', {})
            # Event usually contains models if using model_validate, but WS might still be dicts
            # We handle both for resilience
            platform = data.get('provider', event.get('provider', 'unknown'))
            if hasattr(platform, 'value'):
                platform = platform.value
                
            parts = data.get('message_parts', [])
            message = "".join([p.get('text', '') for p in parts]) or data.get('message', '')
            access_level = data.get('viewer_access_level')

            Formatter.chat(
                platform,
                data.get('viewer_display_name', 'System'),
                message,
                access_level=access_level
            )

        @self.client.ws.on("activity")
        async def on_activity(event):
            data = event.get('data', {})
            platform = data.get('provider', event.get('provider', 'synchra'))
            if hasattr(platform, 'value'):
                platform = platform.value
                
            action = event.get('action', 'triggered')
            activity_type = data.get('type', 'event')
            viewer = data.get('viewer_display_name', 'Someone')
            
            Formatter.activity(
                platform,
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
            
            if result.success > 0:
                Formatter.info(f"Broadcasted message to {result.success} platforms.")
            if result.failed > 0:
                for err in result.errors:
                    p_name = err.platform.value.upper()
                    Formatter.error(f"Failed to send to {p_name}: {err.error}")
        except Exception as e:
            Formatter.error(f"Broadcast failed: {e}")
