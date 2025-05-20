from lightning_app import LightningApp, LightningFlow
from lightning_app.components.python import TracerPythonScript

class RootFlow(LightningFlow):
    def __init__(self):
        super().__init__()
        self.api = TracerPythonScript(
            script_path="serve.py",
            port=8080
        )

    def run(self):
        self.api.run()

    def configure_layout(self):
        return [{"name": "API", "content": self.api}]

app = LightningApp(RootFlow())
