from flask import Blueprint, request, jsonify
import random
import time

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Development-only OTP storage
otp_store = {}

OTP_EXPIRY_SECONDS = 300  # 5 minutes


@auth_bp.route("/send-otp", methods=["POST"])
def send_otp():
    data = request.get_json(silent=True) or {}

    identifier = data.get("identifier")

    if not identifier:
        return jsonify({
            "success": False,
            "message": "Phone number or email is required"
        }), 400

    identifier = identifier.strip()

    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # Store OTP with expiry
    otp_store[identifier] = {
        "otp": otp,
        "created_at": time.time()
    }

    # DEVELOPMENT ONLY
    print(f"\n[DEV OTP] {identifier} -> {otp}\n")

    return jsonify({
        "success": True,
        "message": "OTP generated successfully",
        "development_otp": otp
    }), 200


@auth_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json(silent=True) or {}

    identifier = data.get("identifier")
    otp = data.get("otp")

    if not identifier or not otp:
        return jsonify({
            "success": False,
            "message": "Identifier and OTP are required"
        }), 400

    identifier = identifier.strip()
    otp = str(otp).strip()

    stored = otp_store.get(identifier)

    if not stored:
        return jsonify({
            "success": False,
            "message": "OTP not found. Please request a new OTP."
        }), 400

    # Check expiry
    if time.time() - stored["created_at"] > OTP_EXPIRY_SECONDS:
        otp_store.pop(identifier, None)

        return jsonify({
            "success": False,
            "message": "OTP expired. Please request a new OTP."
        }), 400

    # Check OTP
    if otp != stored["otp"]:
        return jsonify({
            "success": False,
            "message": "Invalid OTP"
        }), 401

    # OTP can only be used once
    otp_store.pop(identifier, None)

    return jsonify({
        "success": True,
        "message": "Login successful",
        "user": {
            "identifier": identifier
        }
    }), 200