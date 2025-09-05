#!/usr/bin/env python3
"""
Generate dummy events using EventsController.track_events (bulk) for testing Nova Manager
"""

import random
from datetime import datetime, timedelta, timezone
import traceback
from typing import Dict, Any, List
from uuid import UUID

from nova_manager.components.metrics.events_controller import EventsController
from nova_manager.components.users.models import Users
from nova_manager.database.session import SessionLocal
from sqlalchemy.orm import Session

# Import event listeners to register them with SQLAlchemy
from nova_manager.components.users import event_listeners  # noqa: F401
from nova_manager.components.user_experience import (
    event_listeners as ux_event_listeners,
)  # noqa: F401


class TestEventGenerator:
    def __init__(
        self, db: Session, organisation_id: str = "org123", app_id: str = "app123"
    ):
        self.db = db
        self.organisation_id = organisation_id
        self.app_id = app_id
        self.events_controller = EventsController(organisation_id, app_id)

        # Generate a pool of user IDs to simulate realistic usage
        self.user_pool = [
            f"user_{i + 1:03d}" for i in range(20)
        ]  # String user IDs like "user_001", "user_002", etc.

        # Define realistic event types and properties
        self.event_templates = {
            "user_signup": {
                "signup_method": ["email", "google", "facebook", "apple"],
                "user_type": ["free", "premium", "trial"],
                "referral_source": ["organic", "paid_search", "social", "email"],
                "plan_type": ["basic", "pro", "enterprise"],
            },
            "purchase_completed": {
                "amount": lambda: round(random.uniform(9.99, 299.99), 2),
                "currency": ["USD", "EUR", "GBP"],
                "product_category": ["electronics", "clothing", "software", "books"],
                "payment_method": ["credit_card", "paypal", "apple_pay", "stripe"],
                "discount_applied": [True, False],
            },
            "page_view": {
                "page_name": ["home", "product", "checkout", "profile", "settings"],
                "page_category": ["landing", "catalog", "account", "support"],
                "device_type": ["desktop", "mobile", "tablet"],
                "session_duration": lambda: random.randint(30, 600),
                "page_load_time": lambda: round(random.uniform(0.5, 3.0), 2),
            },
            "button_click": {
                "button_name": ["cta_signup", "add_to_cart", "checkout", "subscribe"],
                "page_name": ["home", "product", "pricing", "blog"],
                "element_position": ["header", "hero", "sidebar", "footer"],
                "ab_test_variant": ["A", "B", "control"],
            },
            "video_watch": {
                "video_id": lambda: f"video_{random.randint(1, 100)}",
                "video_duration": lambda: random.randint(60, 1800),
                "watch_duration": lambda: random.randint(10, 1800),
                "video_category": ["tutorial", "demo", "testimonial", "entertainment"],
                "completion_rate": lambda: round(random.uniform(0.1, 1.0), 2),
            },
            "email_opened": {
                "campaign_id": lambda: f"camp_{random.randint(1, 50)}",
                "campaign_name": ["welcome_series", "promotional", "newsletter"],
                "email_type": ["marketing", "transactional", "notification"],
                "subject_line": ["Welcome!", "Special Offer", "Your Order"],
            },
            "search_performed": {
                "search_query": ["laptop", "shoes", "tutorial", "pricing", "help"],
                "search_category": ["products", "help", "content"],
                "results_count": lambda: random.randint(0, 100),
                "result_clicked": [True, False],
            },
            "app_session_start": {
                "app_version": ["1.0.0", "1.1.0", "1.2.0", "2.0.0"],
                "platform": ["iOS", "Android", "Web"],
                "device_model": ["iPhone_14", "Samsung_S21", "Desktop"],
                "session_count": lambda: random.randint(1, 50),
            },
        }

    def generate_event_data(self, event_name: str) -> Dict[str, Any]:
        """Generate realistic event data for the given event type"""
        if event_name not in self.event_templates:
            return {}

        template = self.event_templates[event_name]
        event_data = {}

        for key, value_options in template.items():
            if callable(value_options):
                # Execute lambda function for dynamic values
                event_data[key] = value_options()
            elif isinstance(value_options, list):
                # Choose random value from list
                event_data[key] = random.choice(value_options)
            else:
                event_data[key] = value_options

        return event_data

    def create_test_users(self) -> List[UUID]:
        """Get or create test users in the database with comprehensive user profiles"""
        user_pids = []  # Store the actual UUID pids for event tracking
        created_count = 0
        existing_count = 0

        print("👥 Getting or creating test users with comprehensive profiles...")

        for i, user_id in enumerate(self.user_pool):
            # Check if user already exists
            existing_user = (
                self.db.query(Users)
                .filter(
                    Users.user_id == user_id,
                    Users.organisation_id == self.organisation_id,
                    Users.app_id == self.app_id,
                )
                .first()
            )

            if existing_user:
                # User exists, use existing pid
                user_pids.append(existing_user.pid)
                existing_count += 1
                print(
                    f"✅ User {i + 1} ({user_id}): Found existing user (pid: {existing_user.pid})"
                )
            else:
                # User doesn't exist, create new one
                # Generate comprehensive user profile data
                signup_days_ago = random.randint(1, 365)
                signup_date = datetime.now(timezone.utc) - timedelta(
                    days=signup_days_ago
                )

                user_profile = {
                    # Demographics
                    "age": random.randint(18, 65),
                    "gender": random.choice(
                        ["male", "female", "other", "prefer_not_to_say"]
                    ),
                    "country": random.choice(
                        ["US", "UK", "CA", "AU", "DE", "FR", "JP", "BR"]
                    ),
                    "city": random.choice(
                        [
                            "New York",
                            "London",
                            "Toronto",
                            "Sydney",
                            "Berlin",
                            "Paris",
                            "Tokyo",
                            "São Paulo",
                        ]
                    ),
                    "timezone": random.choice(
                        ["UTC-8", "UTC-5", "UTC", "UTC+1", "UTC+9"]
                    ),
                    # Subscription & Business
                    "subscription_plan": random.choice(
                        ["free", "basic", "premium", "enterprise"]
                    ),
                    "subscription_status": random.choice(
                        ["active", "trial", "expired", "cancelled"]
                    ),
                    "account_type": random.choice(
                        ["personal", "business", "student", "non_profit"]
                    ),
                    "signup_date": signup_date.isoformat(),
                    "last_login_date": (
                        datetime.now(timezone.utc)
                        - timedelta(days=random.randint(0, 30))
                    ).isoformat(),
                    # Financial
                    "total_spent": round(random.uniform(0, 2000), 2),
                    "average_order_value": round(random.uniform(10, 200), 2),
                    "lifetime_value": round(random.uniform(50, 5000), 2),
                    "payment_method": random.choice(
                        ["credit_card", "paypal", "bank_transfer", "crypto"]
                    ),
                    # Engagement & Behavior
                    "total_sessions": random.randint(1, 200),
                    "total_events": random.randint(10, 1000),
                    "avg_session_duration": round(random.uniform(60, 1800), 1),
                    "last_active_days_ago": random.randint(0, 30),
                    "engagement_score": round(random.uniform(0, 100), 1),
                    # Preferences & Marketing
                    "marketing_consent": random.choice([True, False]),
                    "newsletter_subscribed": random.choice([True, False]),
                    "push_notifications_enabled": random.choice([True, False]),
                    "preferred_language": random.choice(
                        ["en", "es", "fr", "de", "pt", "ja"]
                    ),
                    "communication_frequency": random.choice(
                        ["daily", "weekly", "monthly", "never"]
                    ),
                    # Technical
                    "device_type": random.choice(["desktop", "mobile", "tablet"]),
                    "operating_system": random.choice(
                        ["Windows", "macOS", "iOS", "Android", "Linux"]
                    ),
                    "browser": random.choice(
                        ["Chrome", "Safari", "Firefox", "Edge", "Opera"]
                    ),
                    "app_version": random.choice(
                        ["1.0.0", "1.1.0", "1.2.0", "2.0.0", "2.1.0"]
                    ),
                    # Acquisition & Attribution
                    "acquisition_channel": random.choice(
                        [
                            "organic_search",
                            "paid_search",
                            "social_media",
                            "email",
                            "referral",
                            "direct",
                        ]
                    ),
                    "referral_source": random.choice(
                        [
                            "google",
                            "facebook",
                            "twitter",
                            "linkedin",
                            "friend",
                            "advertisement",
                        ]
                    ),
                    "utm_campaign": random.choice(
                        ["summer_sale", "new_user", "retargeting", "brand_awareness"]
                    ),
                    "first_touch_channel": random.choice(
                        ["organic", "paid", "social", "email", "direct"]
                    ),
                    # Segmentation
                    "user_segment": random.choice(
                        ["new_user", "active_user", "at_risk", "champion", "dormant"]
                    ),
                    "customer_tier": random.choice(
                        ["bronze", "silver", "gold", "platinum"]
                    ),
                    "cohort_month": signup_date.strftime("%Y-%m"),
                    "is_premium": random.choice([True, False]),
                    "is_power_user": random.choice([True, False]),
                }

                # Create new user in database
                user = Users(
                    user_id=user_id,
                    organisation_id=self.organisation_id,
                    app_id=self.app_id,
                    user_profile=user_profile,
                )

                self.db.add(user)
                self.db.flush()  # Flush to get the generated pid
                user_pids.append(user.pid)  # Store the UUID pid for event tracking
                created_count += 1
                print(
                    f"✅ User {i + 1} ({user_id}): Created new user with {len(user_profile)} properties (pid: {user.pid})"
                )

        # Commit all changes - track_user_profile will be called automatically via event listener for new users
        if created_count > 0:
            self.db.commit()
            print(
                f"📝 {created_count} new user profiles automatically tracked via SQLAlchemy event listener"
            )

        print(
            f"📊 Summary: {existing_count} existing users found, {created_count} new users created"
        )

        return user_pids

    def generate_historical_events(
        self, days: int = 7, events_per_day: int = 50
    ) -> int:
        """Generate historical events over the specified number of days using bulk tracking"""
        total_events = 0

        print(
            f"🚀 Generating {days} days of historical events ({events_per_day} events/day)..."
        )

        for day in range(days, 0, -1):
            current_date = datetime.now(timezone.utc) - timedelta(days=day)

            # Collect events by user for bulk sending
            user_events = {user_id: [] for user_id in self.user_pool}

            for _ in range(events_per_day):
                # Random user and event type
                user_id = random.choice(self.user_pool)
                event_name = random.choice(list(self.event_templates.keys()))

                # Generate timestamp within the day
                hour_offset = random.randint(0, 23)
                minute_offset = random.randint(0, 59)
                event_timestamp = current_date.replace(
                    hour=hour_offset, minute=minute_offset, second=random.randint(0, 59)
                )

                # Generate event data
                event_data = self.generate_event_data(event_name)

                # Add event to user's batch
                user_events[user_id].append(
                    {
                        "event_name": event_name,
                        "event_data": event_data,
                        "timestamp": event_timestamp,
                    }
                )

            # Send events in bulk for each user
            day_events = 0
            for user_id, events in user_events.items():
                if events:  # Only send if user has events for this day
                    try:
                        # Track events in bulk using EventsController
                        self.events_controller.track_events(
                            user_id=user_id, events=events
                        )
                        day_events += len(events)
                        total_events += len(events)

                    except Exception as e:
                        print(
                            f"❌ Error tracking {len(events)} events for user {user_id}: {e}"
                        )

            print(
                f"✅ Day -{day}: Generated {day_events} events across {len([u for u, e in user_events.items() if e])} users"
            )

        return total_events

    def generate_real_time_events(self, count: int = 20) -> int:
        """Generate recent events for immediate testing using bulk tracking"""

        print(f"⚡ Generating {count} recent events...")

        # Collect events by user for bulk sending
        user_events = {user_id: [] for user_id in self.user_pool}

        for i in range(count):
            user_id = random.choice(self.user_pool)
            event_name = random.choice(list(self.event_templates.keys()))

            # Recent timestamp (within last hour)
            timestamp = datetime.now(timezone.utc) - timedelta(
                minutes=random.randint(0, 60)
            )
            event_data = self.generate_event_data(event_name)

            # Add event to user's batch
            user_events[user_id].append(
                {
                    "event_name": event_name,
                    "event_data": event_data,
                    "timestamp": timestamp,
                }
            )

        # Send events in bulk for each user
        successful = 0
        for user_id, events in user_events.items():
            if events:  # Only send if user has events
                try:
                    self.events_controller.track_events(user_id=user_id, events=events)
                    successful += len(events)
                    print(
                        f"✅ User {str(user_id)[:8]}...: Sent {len(events)} events in bulk"
                    )

                except Exception as e:
                    print(
                        f"❌ User {str(user_id)[:8]}...: Failed to send {len(events)} events: {e}"
                    )

        return successful


def main():
    """Main function to generate test events"""
    print("🎯 Nova Manager Test Event Generator")
    print("=" * 50)

    # Configuration
    ORGANISATION_ID = "org123"
    APP_ID = "app123"
    DAYS_OF_HISTORY = 7
    EVENTS_PER_DAY = 100
    RECENT_EVENTS = 50

    try:
        db = SessionLocal()
        generator = TestEventGenerator(db, ORGANISATION_ID, APP_ID)

        # Step 1: Get or create test users with comprehensive profiles
        print("\n👥 Getting or creating test users with comprehensive profiles...")
        user_pids = generator.create_test_users()
        generator.user_pool = (
            user_pids  # Update user_pool with actual user PIDs for event tracking
        )
        print(
            f"✅ Ready with {len(user_pids)} test users with 30+ profile properties each"
        )

        # Step 2: Generate historical events in bulk
        print("\n📊 Generating historical events using bulk tracking...")
        historical_count = generator.generate_historical_events(
            days=DAYS_OF_HISTORY, events_per_day=EVENTS_PER_DAY
        )

        # Step 3: Generate recent events in bulk
        print("\n⚡ Generating recent events using bulk tracking...")
        recent_count = generator.generate_real_time_events(RECENT_EVENTS)

        # Summary
        total_events = historical_count + recent_count
        print("\n🎉 Event Generation Complete! (Using Bulk Tracking)")
        print(f"📈 Total events generated: {total_events}")
        print(f"📊 Historical events: {historical_count} ({DAYS_OF_HISTORY} days)")
        print(f"⚡ Recent events: {recent_count}")
        print(f"👥 Users: {len(user_pids)}")
        print(f"🏷️  Event types: {list(generator.event_templates.keys())}")
        print("🚀 Performance: Events sent in bulk batches per user")

        print("\n🧪 Test your metric builder with:")
        print("- Count metrics: 'user_signup', 'purchase_completed', 'page_view'")
        print("- Aggregation metrics: sum of 'amount', avg 'session_duration'")
        print("- Ratio metrics: purchase_completed / user_signup")
        print(
            "- Group by event properties: 'device_type', 'payment_method', 'platform'"
        )
        print("- Group by user profile: 'country', 'subscription_plan', 'user_segment'")
        print(
            "- Filter by event properties: 'currency', 'ab_test_variant', 'product_category'"
        )
        print(
            "- Filter by user profile: 'age', 'country', 'subscription_plan', 'customer_tier'"
        )
        print("\n📊 User Profile Properties Available for Filtering:")
        print("  Demographics: age, gender, country, city, timezone")
        print("  Subscription: subscription_plan, subscription_status, account_type")
        print("  Financial: total_spent, average_order_value, lifetime_value")
        print("  Engagement: total_sessions, engagement_score, last_active_days_ago")
        print("  Technical: device_type, operating_system, browser, app_version")
        print("  Marketing: acquisition_channel, utm_campaign, marketing_consent")
        print("  Segmentation: user_segment, customer_tier, is_premium, is_power_user")

    except Exception as e:
        traceback.print_exc()
        print(f"❌ Error: {e}")
        print(
            "Make sure your database is set up and Nova Manager dependencies are installed"
        )
        db.rollback()
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    main()
