from django.db import models

class Klientas(models.Model):
    vardas = models.CharField(max_length=100)
    adresas = models.CharField(max_length=255, blank=True, null=True)
    telefonas = models.CharField(max_length=20)
    email = models.TextField(default='')

    class Meta:
        verbose_name = 'Klientas'
        verbose_name_plural = 'Klientai'

    def __str__(self):
        return self.vardas

class Projektas(models.Model):
    klientas = models.ForeignKey(Klientas, on_delete=models.CASCADE)  # Ryšys su Klientas modeliu
    pavadinimas = models.CharField(max_length=255)
    uzklausos_data = models.DateField(null=True, blank=True)
    pasiulymo_data = models.DateField(null=True, blank=True)

    def formatted_uzklausos_data(self):
        return self.uzklausos_data.strftime('%Y-%m-%d')

    def formatted_pasiulymo_data(self):
        return self.pasiulymo_data.strftime('%Y-%m-%d')
    
    class Meta:
        verbose_name = 'Projektas'
        verbose_name_plural = 'Projektai'

    def __str__(self):
        return self.pavadinimas

class Danga(models.Model):
    pavadinimas = models.CharField(max_length=50, choices=[
        ('KTL', 'KTL'),
        ('miltai', 'miltai'),
        ('KTL+miltai', 'KTL+miltai'),
        ('ZnPhos', 'ZnPhos'),
        ('Plovimas', 'Plovimas'),
        ('Papildomos paslaugos', 'Papildomos paslaugos'),
        ('Etiketavimas', 'Etiketavimas'),
    ])
    def __str__(self):
        return self.pavadinimas

class Detale(models.Model):
    pavadinimas = models.CharField(max_length=255)
    brezinio_nr = models.CharField(max_length=255)
    plotas = models.FloatField()
    svoris = models.FloatField()
    kiekis_metinis = models.IntegerField()
    kiekis_menesis = models.IntegerField(blank=True, null=True)
    kiekis_partijai = models.IntegerField()
    ppap_dokumentai = models.TextField()
    danga = models.ManyToManyField('Danga', blank=True)
    standartas = models.CharField(max_length=255, blank=True, null=True)
    kabinimo_tipas = models.CharField(max_length=255, blank=True, null=True)
    kabinimas_xyz = models.CharField(max_length=255, blank=True, null=True)
    kiekis_reme = models.IntegerField(blank=True, null=True)
    faktinis_kiekis_reme = models.IntegerField(blank=True, null=True)
    pakavimas = models.CharField(max_length=255, blank=True, null=True)
    nuoroda_brezinio = models.CharField(max_length=255, blank=True, null=True)
    nuoroda_pasiulymo = models.CharField(max_length=255, blank=True, null=True)
    pastabos = models.TextField(blank=True, null=True)
    projektas = models.ForeignKey(Projektas, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Detale'
        verbose_name_plural = 'Detalės'

    def __str__(self):
        return self.pavadinimas

class Kaina(models.Model):
    MATAS_CHOICES = [
        ('vnt.', 'vnt.'),
        ('kg', 'kg')
    ]
    detalė = models.ForeignKey(Detale, on_delete=models.CASCADE, related_name='kainos')
    busena = models.CharField(max_length=20, choices=[('aktuali', 'aktuali'), ('sena', 'sena')])
    suma = models.FloatField()
    yra_fiksuota = models.BooleanField(default=False)
    kiekis_nuo = models.IntegerField(blank=True, null=True)
    kiekis_iki = models.IntegerField(blank=True, null=True)
    fiksuotas_kiekis = models.IntegerField(default=100, null=True)
    kainos_matas = models.CharField(max_length=10, choices=MATAS_CHOICES, default='vnt.')
    
    class Meta:
        verbose_name = 'Kaina'
        verbose_name_plural = 'Kainos'

    def __str__(self):
        return f"{self.detalė.pavadinimas} - {self.suma} EUR"

class Uzklausa(models.Model):
    klientas = models.ForeignKey(Klientas, on_delete=models.CASCADE)
    projektas = models.ForeignKey(Projektas, on_delete=models.CASCADE)
    detale = models.ForeignKey(Detale, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = 'Užklausa'
        verbose_name_plural = 'Užklausos'

    def __str__(self):
        return f"{self.klientas.vardas} - {self.projektas.pavadinimas} - {self.detale.pavadinimas}"
