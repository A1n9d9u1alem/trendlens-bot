from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import User, Payment, get_db

class PaymentHandler:
    def __init__(self):
        self.bank_details = {
            'bank': 'Commercial Bank of Ethiopia',
            'account': '1000531726988',
            'name': 'Andualem Argo'
        }
        self.mobile_money = {
            'provider': 'M-Pesa / Telebirr',
            'number': '+251972762813',
            'name': 'Andualem Argo'
        }
    
    def get_payment_message(self):
        return (
            "💎 TrendLens AI Pro - 30 Days\n"
            "💰 Price: 300 ETB / $5 USD\n\n"
            "📱 Payment Methods:\n\n"
            "1️⃣ Bank Transfer\n"
            f"🏦 {self.bank_details['bank']}\n"
            f"💳 Account: {self.bank_details['account']}\n"
            f"👤 Name: {self.bank_details['name']}\n\n"
            "2️⃣ Mobile Money\n"
            f"📱 {self.mobile_money['provider']}\n"
            f"📞 Number: {self.mobile_money['number']}\n"
            f"👤 Name: {self.mobile_money['name']}\n\n"
            "After payment, confirm using:\n"
            "/confirm <reference_number>\n\n"
            "Example: /confirm TX123456789\n\n"
            "💬 Support: Contact admin for help"
        )
    
    def create_payment_request(self, user_id: int, amount: float, db: Session):
        payment = Payment(
            user_id=user_id,
            amount=amount,
            status='pending'
        )
        db.add(payment)
        db.commit()
        return payment
    
    def confirm_payment(self, user_id: int, reference: str, db: Session):
        payment = db.query(Payment).filter(
            Payment.user_id == user_id,
            Payment.status == 'pending'
        ).order_by(Payment.created_at.desc()).first()
        
        if payment:
            payment.reference = reference
            payment.status = 'submitted'
            db.commit()
            return True
        return False
    
    def approve_payment(self, user_id: int, days: int, db: Session):
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        payment = db.query(Payment).filter(
            Payment.user_id == user_id,
            Payment.status == 'submitted'
        ).order_by(Payment.created_at.desc()).first()
        
        if payment:
            payment.status = 'approved'
            payment.approved_at = datetime.utcnow()
        
        user.is_premium = True
        if user.subscription_end and user.subscription_end > datetime.utcnow():
            user.subscription_end += timedelta(days=days)
        else:
            user.subscription_end = datetime.utcnow() + timedelta(days=days)
        
        db.commit()
        return True
    
    def reject_payment(self, user_id: int, db: Session):
        payment = db.query(Payment).filter(
            Payment.user_id == user_id,
            Payment.status == 'submitted'
        ).order_by(Payment.created_at.desc()).first()
        
        if payment:
            payment.status = 'rejected'
            db.commit()
            return True
        return False
