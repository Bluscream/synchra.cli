import asyncio
import logging
from typing import Optional, List
from uuid import UUID

from synchra import SynchraClient
from .formatter import Formatter

class SynchraObserver:
    """The main logic for the Synchra CLI Observer."""
    
    def __init__(self, client: SynchraClient):
        self.client = client
        self.channel_id: Optional[UUID] = None
        self.channel_providers: List[dict] = []
        self.user_provider_id: Optional[UUID] = None

    async def setup(self, channel_id: Optional[UUID] = None, provider: Optional[str] = None, name: Optional[str] = None):
        """Find the channel and setup the observer."""
        if channel_id:
            self.channel_id = channel_id
            Formatter.info(f"Using channel ID: {self.channel_id}")
        elif provider and name:
            Formatter.info(f"Resolving channel: {provider}/{name}...")
            
            # 1. Resolve Channel using efficient filters
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

        # 2. Ensure we have providers (if we bypassed the loop with channel_id)
        if not self.channel_providers:
            self.channel_providers = await self.client.channels.list_providers(self.channel_id)
        
        Formatter.info(f"Connected to channel {self.channel_id} with {len(self.channel_providers)} providers.")

        # 3. Get User's own provider to act as sender
        # We'll just pick the first one available
        user_providers = await self.client.http.get("/api/2/user/providers")
        if user_providers:
            # Note: user_providers is a list of Dicts or models based on SDK implementation
            self.user_provider_id = UUID(user_providers[0]['id'])
            Formatter.info(f"Using user provider {self.user_provider_id} for sending messages.")
        else:
            Formatter.error("No linked providers found for your account. You won't be able to chat.")

        # 3. Setup WebSocket handlers
        @self.client.ws.on("chat_message")
        async def on_chat(event):
            data = event.get('data', {})
            # Provider is usually in data, fallback to event root
            provider = data.get('provider', event.get('provider', 'unknown'))
            # Handle Enums if needed
            if hasattr(provider, 'value'):
                provider = provider.value
                
            # Message is stored in message_parts (list of MessagePart1)
            message_parts = data.get('message_parts', [])
            message = "".join([p.get('text', '') for p in message_parts])
            if not message:
                message = data.get('message', '') # Fallback

            Formatter.chat(
                provider,
                data.get('viewer_display_name', 'System'),
                message
            )

        @self.client.ws.on("activity")
        async def on_activity(event):
            data = event.get('data', {})
            # Provider identification logic
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
        """Send a message to all providers of the channel."""
        if not self.user_provider_id:
            Formatter.error("Cannot send: No user provider available.")
            return

        sent_to = []
        for provider in self.channel_providers:
            try:
                # 1. Skip providers that don't support sending or aren't active
                p_member = getattr(provider, 'provider', 'unknown')
                p_type = str(getattr(p_member, 'value', p_member)).lower()
                
                # TikTok doesn't support sending via Synchra usually
                if p_type == "tiktok":
                    continue
                
                # Check for stream_chat_id (required for YouTube and often useful for others)
                chat_id = getattr(provider, 'stream_chat_id', None)
                if p_type == "youtube" and not chat_id:
                    continue

                p_id = str(getattr(provider, 'id'))
                
                # payload: user_provider_id, channel_provider_id, message
                data = {
                    "user_provider_id": str(self.user_provider_id),
                    "channel_provider_id": p_id,
                    "message": message
                }
                await self.client.http.post("/api/2/chat/messages", json=data)
                sent_to.append(p_type.upper())
            except Exception as e:
                p_member = getattr(provider, 'provider', 'unknown')
                p_type = str(getattr(p_member, 'value', p_member)).upper()
                Formatter.error(f"Failed to send to {p_type}: {e}")
        
        if sent_to:
            Formatter.info(f"Message broadcasted to: {', '.join(sent_to)}")
        elif not any(getattr(p, 'provider', '').lower() == 'tiktok' for p in self.channel_providers):
            # If nothing was sent and it wasn't just a tiktok-only channel
            Formatter.error("Message was not sent to any active platforms.")
