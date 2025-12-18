from flask import Flask, jsonify, request

app = Flask(__name__)

##################
# Health Checks
##################
@app.get("/health")
def health_check():
    return jsonify(status="ok"), 200

@app.get("/hello")
def hello_test():
    name = request.args.get("name", "World")
    return jsonify(message=f"Hello, {name}!")

if __name__ == '__main__':
    app.run(debug=True)