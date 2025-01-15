from channels.generic.websocket import AsyncJsonWebsocketConsumer


class JobConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']

        await self.channel_layer.group_add(
            "job_" + self.session_id,
            self.channel_name
        )

        await self.accept()
        await self.send_json({
            "message": {"type": "notification", "content": "Connected to job session."}
        })

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            "job_" + self.session_id,
            self.channel_name
        )

    async def receive_json(self, content, **kwargs):
        await self.channel_layer.group_send(
            "job_" + self.session_id,
            {
                "type": "job_message",
                "message": content
            }
        )

    async def job_message(self, event):
        await self.send_json({"message": event})

