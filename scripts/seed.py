"""
EasyBill - Seed initial data (admin user + company)
รันครั้งเดียวหลังติดตั้ง
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app, db
from app.models import User, Company


def seed():
    app = create_app('production')
    with app.app_context():
        db.create_all()

        # Default admin
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                full_name='ผู้ดูแลระบบ',
                email='admin@example.com',
                role='admin',
                is_active=True,
            )
            admin.set_password('admin1234')
            db.session.add(admin)
            print('✓ สร้างผู้ใช้ admin (รหัสผ่าน: admin1234)')
        else:
            print('• ผู้ใช้ admin มีอยู่แล้ว ข้าม')

        # Default company
        company = Company.query.first()
        if not company:
            company = Company(
                name='บริษัทของฉัน จำกัด',
                branch='สำนักงานใหญ่',
                default_vat_rate=7.0,
                default_terms='ยืนราคา 30 วัน\nเงื่อนไขการชำระเงิน: เครดิต 30 วัน',
            )
            db.session.add(company)
            print('✓ สร้างข้อมูลกิจการเริ่มต้น')
        else:
            print('• ข้อมูลกิจการมีอยู่แล้ว ข้าม')

        db.session.commit()
        print('\nเสร็จสิ้น! เข้าใช้งานด้วย admin / admin1234')
        print('** กรุณาเปลี่ยนรหัสผ่านหลังเข้าใช้ครั้งแรก **')


if __name__ == '__main__':
    seed()
