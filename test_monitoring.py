"""
Test Error Monitoring System
Run this to verify error monitoring is working
"""

from error_monitor import error_monitor
import time


def test_error_monitoring():
    print("=" * 50)
    print("Testing Error Monitoring System")
    print("=" * 50)
    print()
    
    # Check if Sentry is enabled
    if error_monitor.sentry_enabled:
        print("✅ Sentry is ENABLED")
        print(f"   Environment: {error_monitor.environment}")
    else:
        print("📝 Using LOCAL LOGGING (Sentry not configured)")
        print("   Errors will be saved to logs/error.log")
    
    print()
    print("Running tests...")
    print()
    
    # Test 1: Capture message
    print("1. Testing message capture...")
    error_monitor.capture_message("Test message from monitoring system", level='info')
    print("   ✅ Message sent")
    time.sleep(1)
    
    # Test 2: Capture warning
    print("2. Testing warning capture...")
    error_monitor.capture_message("Test warning", level='warning')
    print("   ✅ Warning sent")
    time.sleep(1)
    
    # Test 3: Capture error
    print("3. Testing error capture...")
    try:
        # Intentional error
        result = 1 / 0
    except Exception as e:
        error_monitor.capture_exception(e, context={
            'test': 'error_monitoring',
            'type': 'division_by_zero'
        })
        print("   ✅ Error captured")
    time.sleep(1)
    
    # Test 4: User context
    print("4. Testing user context...")
    error_monitor.set_user(user_id=12345, username="test_user")
    error_monitor.capture_message("Message with user context", level='info')
    print("   ✅ User context set")
    time.sleep(1)
    
    # Test 5: Breadcrumbs
    print("5. Testing breadcrumbs...")
    error_monitor.add_breadcrumb(
        message="User clicked button",
        category="user_action",
        data={'button': 'subscribe'}
    )
    error_monitor.capture_message("Event with breadcrumb", level='info')
    print("   ✅ Breadcrumb added")
    
    print()
    print("=" * 50)
    print("Tests Complete!")
    print("=" * 50)
    print()
    
    if error_monitor.sentry_enabled:
        print("📊 Check your Sentry dashboard:")
        print("   https://sentry.io/organizations/your-org/issues/")
        print()
        print("   You should see:")
        print("   - 3 info messages")
        print("   - 1 warning")
        print("   - 1 error (division by zero)")
    else:
        print("📝 Check local logs:")
        print("   logs/error.log")
        print()
        print("   To enable Sentry:")
        print("   1. Sign up at https://sentry.io")
        print("   2. Add SENTRY_DSN to .env")
        print("   3. Run this test again")
    
    print()


if __name__ == '__main__':
    test_error_monitoring()
