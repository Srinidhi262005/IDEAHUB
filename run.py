import os
from Ideahub import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "0") in ("1", "true", "True")
    app.run(
        host="127.0.0.1",
        port=port,
        debug=debug
    )


    












