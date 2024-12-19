from django.contrib.auth import get_user_model, authenticate, update_session_auth_hash
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.exceptions import AuthenticationFailed
from ninja import Router, Schema
from ninja.pagination import paginate
from ninja.responses import Response
from typing import List, Optional
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist
from .models import Blog, Tag, Category, Menu
from django.shortcuts import get_object_or_404
from django.db.models import Q
from datetime import date

router = Router()

class RegisterRequest(Schema):
    username: str
    email: str
    password: str

class LoginRequest(Schema):
    username: str
    password: str

class ChangePasswordRequest(Schema):
    new_password: str
    confirm_password: str

class ModifyProfileRequest(Schema):
    username: str = None
    email: str = None

class AuthorOut(Schema):
    id: int
    username: str

class TagOut(Schema):
    id: int
    title: str

class CategoryOut(Schema):
    id: int
    title: str

class BlogOut(Schema):
    id: int
    title: str
    description: str
    created_at: date
    author: AuthorOut
    tags: List[TagOut]
    category: Optional[CategoryOut]

class BlogFilters(Schema):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    author_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None
    category_ids: Optional[List[int]] = None

class BlogCreateRequest(Schema):
    title: str
    description: str
    picture: str 
    category_id: int 
    tags: List[int] 


class CategoryOut(Schema):
    id: int
    title: str
    parent: Optional[int] 

class TagOut(Schema):
    id: int
    title: str

class MenuOut(Schema):
    id: int
    title: str
    order_number: int
    category_id: Optional[int]
    url_slug: str

@router.post("/register/")
def register(request, payload: RegisterRequest):
    user_data = payload.dict()

    if get_user_model().objects.filter(username=user_data["username"]).exists():
        return Response({"message": "Username already exists."}, status=400)

    if get_user_model().objects.filter(email=user_data["email"]).exists():
        return Response({"message": "Email already exists."}, status=400)

    user_data["is_active"] = False  
    user = get_user_model().objects.create_user(**user_data)

    uid = urlsafe_base64_encode(str(user.pk).encode())
    token = default_token_generator.make_token(user)
    activation_link = f"{settings.FRONTEND_URL}/activate/{uid}/{token}/"

    try:
        send_mail(
            'Activate your account',
            f'Click the link to activate your account: {activation_link}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
    except Exception as e:
        return Response({"message": f"Failed to send email: {str(e)}"}, status=500)

    return Response({"message": "Registration successful. Please check your email to activate your account."}, status=201)


@router.get("/activate/{uid}/{token}")
def activate_account(request, uid: str, token: str):
    try:
        uid = urlsafe_base64_decode(uid).decode()
        user = get_user_model().objects.get(pk=uid)
        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return Response({"message": "Account activated successfully."}, status=200)
        else:
            return Response({"message": "Invalid or expired token."}, status=400)
    except Exception:
        return Response({"message": "Error during activation."}, status=400)


@router.post("/login/")
def login(request, payload: LoginRequest):
    login_data = payload.dict()
    username = login_data["username"]
    password = login_data["password"]

    # Authenticate user
    user = authenticate(username=username, password=password)
    if user:
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=200)
    
    return Response({"message": "Invalid credentials"}, status=401)


@router.post("/change-password/")
def change_password(request, payload: ChangePasswordRequest):
    jwt_auth = JWTAuthentication()
    try:
        user, _ = jwt_auth.authenticate(request)
    except AuthenticationFailed:
        return Response({"message": "Invalid or expired token."}, status=401)

    if payload.new_password != payload.confirm_password:
        return Response({"message": "Passwords do not match."}, status=400)

    user.set_password(payload.new_password)
    user.save()

    update_session_auth_hash(request, user)

    return Response({"message": "Password changed successfully."}, status=200)


@router.put("/modify-profile/")
def modify_profile(request, payload: ModifyProfileRequest):
    jwt_auth = JWTAuthentication()
    try:
        user, _ = jwt_auth.authenticate(request)
    except AuthenticationFailed:
        return Response({"message": "Invalid or expired token."}, status=401)

    if payload.username:
        user.username = payload.username
    if payload.email:
        user.email = payload.email

    user.save()

    return Response({"message": "Profile updated successfully."}, status=200)

@router.get("/blogs/", response=List[BlogOut])
@paginate
def get_blogs(request, filters: BlogFilters = BlogFilters()):
    queryset = Blog.objects.all()

    if filters.start_date and filters.end_date:
        queryset = queryset.filter(created_at__range=[filters.start_date, filters.end_date])
    elif filters.start_date:
        queryset = queryset.filter(created_at__gte=filters.start_date)
    elif filters.end_date:
        queryset = queryset.filter(created_at__lte=filters.end_date)

    if filters.author_id:
        queryset = queryset.filter(author_id=filters.author_id)

    if filters.tag_ids:
        queryset = queryset.filter(tags__id__in=filters.tag_ids).distinct()

    if filters.category_ids:
        queryset = queryset.filter(categories__id__in=filters.category_ids).distinct()

    return [
    BlogOut(
        id=blog.id,
        title=blog.title,
        description=blog.description,
        created_at=blog.created_at.date(),
        author=AuthorOut(id=blog.author.id, username=blog.author.username),
        tags=[TagOut(id=tag.id, title=tag.title) for tag in blog.tags.all()],
        category=CategoryOut(id=blog.category.id, title=blog.category.title) if blog.category else None,
    )
    for blog in queryset
]


@router.post("/blogs/", response=BlogOut)
def create_blog(request, payload: BlogCreateRequest):
    jwt_auth = JWTAuthentication()
    try:
        user, _ = jwt_auth.authenticate(request)
    except AuthenticationFailed:
        return Response({"message": "Invalid or expired token."}, status=401)

    # Check if category exists
    try:
        category = Category.objects.get(id=payload.category_id)
    except ObjectDoesNotExist:
        return Response({"message": "Category not found."}, status=400)

    # Create the blog
    blog = Blog.objects.create(
        title=payload.title,
        description=payload.description,
        author=user, 
        category=category,  
        active=True,  
    )

    if payload.picture:
        blog.picture = payload.picture  
        blog.save()

    if payload.tags:
        tags = Tag.objects.filter(id__in=payload.tags) 
        blog.tags.set(tags) 

    blog.save()

    return Response({"message": "Blog created successfully.", "blog_id": blog.id}, status=201)


@router.delete("/blog/{blog_id}/", response={200: str, 400: str, 401: str, 404: str})
def delete_blog(request, blog_id: int):
    jwt_auth = JWTAuthentication()
    try:
        user, _ = jwt_auth.authenticate(request)
    except AuthenticationFailed:
        return Response({"message": "Invalid or expired token."}, status=401)

    blog = get_object_or_404(Blog, id=blog_id)

    if blog.author != user:
        return Response({"message": "You are not the author of this blog post."}, status=400)

    blog.delete()

    return Response({"message": "Blog post deleted successfully."}, status=200)

@router.get("/categories/", response=List[CategoryOut])
def get_categories(request, parent_id: Optional[int] = None):
    if parent_id:
        categories = Category.objects.filter(parent_id=parent_id)
    else:
        categories = Category.objects.all()
    
    return categories

@router.get("/tags/", response=List[TagOut])
def get_tags(request):
    tags = Tag.objects.all()
    return tags

@router.get("/menus/", response=List[MenuOut])
def get_menus(request, category_id: Optional[int] = None):
    if category_id:
        menus = Menu.objects.filter(category_id=category_id).order_by('order_number')
    else:
        menus = Menu.objects.all().order_by('order_number')
    
    return menus