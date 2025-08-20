from app import db

class Curation(db.Model):
  __tablename__ = 'curations'
  id = db.Column(db.Integer, primary_key=True, autoincrement=True)
  status = db.Column(db.Text) # "needs-moderation", "approved", "denied"
  entity = db.Column(db.Text)
  entity_id = db.Column(db.Text)
  property = db.Column(db.Text)
  property_value = db.Column(db.Text)
  create_new = db.Column(db.Boolean, nullable=False, default=False)
  submitter_email = db.Column(db.Text)
  moderator_email = db.Column(db.Text)
  submitted_date = db.Column(db.DateTime)
  moderated_date = db.Column(db.DateTime)
  is_live = db.Column(db.Boolean, nullable=False, default=False)
  live_date = db.Column(db.DateTime)

  def to_dict(self):
    return {
      "id": self.id,
      "status": self.status,
      "entity": self.entity,
      "entity_id": self.entity_id,
      "property": self.property,
      "property_value": self.property_value,
      "create_new": self.create_new,
      "submitter_email": self.submitter_email,
      "moderator_email": self.moderator_email,
      "submitted_date": self.submitted_date,
      "moderated_date": self.moderated_date,
      "is_live": self.is_live,
      "live_date": self.live_date
    }