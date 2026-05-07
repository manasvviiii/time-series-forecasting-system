"""
FASTAPI SERVICE - QUICK TROUBLESHOOTING GUIDE
==============================================

Problem: Cannot access http://0.0.0.0:8000/

SOLUTION:
=========

The address 0.0.0.0:8000 is for SERVER BINDING, not for client access.

To access the API, use:
  • http://localhost:8000/  (if running locally)
  • http://127.0.0.1:8000/  (if running locally)
  • http://<server-ip>:8000/  (if running on remote server)


STEP-BY-STEP:
=============

1. Start the FastAPI service:
   cd c:\Users\manas\Desktop\Test\forecasting
   python main.py

2. You should see:
   INFO:     Uvicorn running on http://0.0.0.0:0.0.0.0:8000
   (Don't use this address - it's for the server)

3. Open in your browser:
   http://localhost:8000/

4. You should see:
   {
     "status": "healthy",
     "data_loaded": true,
     "available_states": 43
   }


ACCESSING ENDPOINTS:
====================

In your browser:
  • Health check: http://localhost:8000/
  • Swagger UI: http://localhost:8000/docs
  • ReDoc UI: http://localhost:8000/redoc
  • List states: http://localhost:8000/states
  • Get forecast: http://localhost:8000/predict/Alabama
  • Metrics: http://localhost:8000/metrics


TESTING WITH CURL:
==================

From command line:
  
  # Health check
  curl http://localhost:8000/

  # List all states
  curl http://localhost:8000/states

  # Get forecast for Alabama
  curl http://localhost:8000/predict/Alabama

  # Pretty print (requires jq)
  curl http://localhost:8000/predict/Alabama | jq .


COMMON ISSUES:
==============

Issue: "Connection refused"
  → FastAPI server is not running
  → Solution: Run `python main.py` first

Issue: "Cannot GET /0.0.0.0:8000"
  → You copied the server binding address wrong
  → Solution: Use http://localhost:8000 instead

Issue: "Port 8000 already in use"
  → Another process is using port 8000
  → Solution: Use different port:
    python main.py --port 8001

Issue: "ModuleNotFoundError"
  → Dependencies not installed
  → Solution: pip install -r requirements.txt


FULL WORKFLOW:
==============

Terminal 1 - Start training:
  python run_training.py

Terminal 2 - Start API (after training is done):
  python main.py

Then in your browser:
  http://localhost:8000/docs


EXPECTED OUTPUT:
================

When you access http://localhost:8000/:

{
  "status": "healthy",
  "data_loaded": true,
  "available_states": 43
}

When you access http://localhost:8000/predict/Alabama:

{
  "state": "Alabama",
  "best_model_used": "XGBoost",
  "forecast_horizon": 8,
  "predictions": [
    12000000.0,
    12500000.0,
    12300000.0,
    12700000.0,
    13000000.0,
    13200000.0,
    13100000.0,
    13500000.0
  ],
  "status": "success"
}


INTERACTIVE DOCUMENTATION:
==========================

FastAPI automatically generates interactive API documentation!

1. Open: http://localhost:8000/docs
   This is the Swagger UI where you can:
   • See all endpoints
   • Try them interactively
   • See request/response examples

2. Alternative: http://localhost:8000/redoc
   This is ReDoc (alternative documentation style)


DEBUGGING:
==========

Enable more verbose logging:

# Option 1: Check logs
tail -f logs/api.log

# Option 2: Run with verbose output
python main.py --log-level debug


ADVANCED:
=========

If you need to access from another machine:

1. Change host to 0.0.0.0 (but then it's less secure):
   In main.py, change:
   uvicorn.run(app, host="0.0.0.0", port=8000)

2. Access from other machine:
   http://<your-computer-ip>:8000/

3. To find your computer's IP:
   Windows: ipconfig (look for IPv4 Address)
   Linux: ifconfig or ip addr


Need more help?
See QUICK_START.md or REFACTORING_SUMMARY.md for more details.
"""
