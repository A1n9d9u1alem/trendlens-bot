"""Monitor database connection pool status"""
from database import engine
from sqlalchemy import text

def check_pool_status():
    pool = engine.pool
    print("=== Database Connection Pool Status ===\n")
    print(f"Pool size: {pool.size()}")
    print(f"Checked out connections: {pool.checkedout()}")
    print(f"Overflow connections: {pool.overflow()}")
    print(f"Checked in connections: {pool.checkedin()}")
    print(f"\nPool configuration:")
    print(f"  Max pool size: {engine.pool._pool.maxsize if hasattr(engine.pool, '_pool') else 'N/A'}")
    print(f"  Max overflow: {engine.pool._max_overflow}")
    print(f"  Timeout: {engine.pool._timeout}s")
    
    # Check active connections in database
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT count(*) as active_connections
                FROM pg_stat_activity
                WHERE datname = current_database()
                AND state = 'active'
            """))
            active = result.fetchone()[0]
            print(f"\nActive database connections: {active}")
    except Exception as e:
        print(f"\nCould not check active connections: {e}")

if __name__ == '__main__':
    check_pool_status()
