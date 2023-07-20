from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.apps import apps

def login_user(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.success(request, ("Возникла ошибка при входе"))
            return redirect('login')
    else:
        return render(request, 'authent/entry.html', {})

def logout_user(request):
    logout(request)
    return redirect('login')

def registration(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            user = authenticate(username=username, password=password)
            landlord = apps.get_model('booking', 'Landlord')
            l = landlord.objects.create(id_landlord_id=user.id)
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'authent/registration.html', {'form': form})


