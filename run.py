from app import create_app

app = create_app()

# Ajoutez ce code pour lister les routes
with app.app_context():
    print("\nRoutes disponibles :")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule}")

if __name__ == '__main__':
    app.run(debug=True)