from app import db

class Curation(db.Model):
  __tablename__ = 'curations'
  id = db.Column(db.Integer, primary_key=True, autoincrement=True)
  entity = db.Column(db.Text)
  entity_id = db.Column(db.Text)
  property = db.Column(db.Text)
  property_value = db.Column(db.Text)
  email = db.Column(db.Text)
  approved = db.Column(db.Boolean)
  ingested = db.Column(db.Boolean)
  submitted_date = db.Column(db.DateTime)
  approved_date = db.Column(db.DateTime)
  ingested_date = db.Column(db.DateTime)

  def to_dict(self):
    return {
      "id": self.id,
      "entity": self.entity,
      "entity_id": self.entity_id,
      "property": self.property,
      "property_value": self.property_value,
      "email": self.email,
      "approved": self.approved,
      "ingested": self.ingested,
      "submitted_date": self.submitted_date,
      "approved_date": self.approved_date,
      "ingested_date": self.ingested_date
    }