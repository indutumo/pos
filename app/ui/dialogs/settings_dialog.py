from app.models.schema import OrganizationProfile

def save_organization_profile(db_session, data):
    """
    Updates the organization profile. Creates it if it doesn't exist.
    'data' should be a dict with keys: name, address, phone, kra_pin
    """
    try:
        profile = db_session.query(OrganizationProfile).first()
        if not profile:
            profile = OrganizationProfile()
            db_session.add(profile)
        
        profile.name = data.get('name')
        profile.address = data.get('address')
        profile.phone = data.get('phone')
        profile.kra_pin = data.get('kra_pin')
        
        db_session.commit()
        return True
    except Exception as e:
        db_session.rollback()
        raise e