import sqlalchemy as sa


metadata = sa.MetaData()

restrictions_tbl = sa.Table("restrictions", metadata,
                            sa.Column("id", sa.Integer, primary_key=True),
                            sa.Column("user", sa.BigInteger, nullable=False),
                            sa.Column("type", sa.String(30), nullable=False, index=True),
                            sa.Column("expiry", sa.DateTime, nullable=True))
