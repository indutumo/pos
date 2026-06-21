from app.models.schema import OrganizationProfile

class OrganizationRepository:
    def __init__(self, db_session):
        self.db = db_session

    def get_profile(self):
        profile = self.db.query(OrganizationProfile).first()
        if not profile:
            profile = OrganizationProfile()
            self.db.add(profile)
            self.db.commit()
        return profile

    def update_profile(self, name, address, phone, kra_pin):
        profile = self.get_profile()
        profile.name = name
        profile.address = address
        profile.phone = phone
        profile.kra_pin = kra_pin
        self.db.commit()
        return profile