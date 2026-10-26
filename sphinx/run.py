from sphinx import create_app

app = create_app()          # gunicorn "run:app" en producción

if __name__ == "__main__":
    app.run(debug=app.config["ENV"] == "development")
