from django.contrib import admin
from .models import Match, Promos, RankedRecord

admin.site.register(Match)
admin.site.register(Promos)
admin.site.register(RankedRecord)
