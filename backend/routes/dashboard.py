from flask import Blueprint

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/", methods=["GET"])
def get_dashboard():
    return {"message": "Dashboard endpoint working"}