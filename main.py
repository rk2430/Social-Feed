import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Protocol
from abc import ABC, abstractmethod
import datetime
import random
from enum import Enum

# ----------------------------------
# Model Layer
# ----------------------------------

class PostType(Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"

@dataclass
class User:
    id: str
    name: str
    username: str
    avatar_url: Optional[str] = None

@dataclass
class Post:
    id: str
    user: User
    content: str
    type: PostType
    likes: int = 0
    comments: int = 0
    shares: int = 0
    timestamp: datetime.datetime = datetime.datetime.now()
    media_url: Optional[str] = None
    liked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user": {
                "id": self.user.id,
                "name": self.user.name,
                "username": self.user.username,
                "avatar_url": self.user.avatar_url
            },
            "content": self.content,
            "type": self.type.value,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "timestamp": self.timestamp.isoformat(),
            "media_url": self.media_url,
            "liked": self.liked
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Post':
        return cls(
            id=data["id"],
            user=User(
                id=data["user"]["id"],
                name=data["user"]["name"],
                username=data["user"]["username"],
                avatar_url=data["user"].get("avatar_url")
            ),
            content=data["content"],
            type=PostType(data["type"]),
            likes=data.get("likes", 0),
            comments=data.get("comments", 0),
            shares=data.get("shares", 0),
            timestamp=datetime.datetime.fromisoformat(data["timestamp"]),
            media_url=data.get("media_url"),
            liked=data.get("liked", False)
        )

class PostRepositoryProtocol(Protocol):
    def fetch_posts(self, limit: int, offset: int) -> List[Post]:
        ...
    
    def like_post(self, post_id: str) -> bool:
        ...
    
    def add_post(self, post: Post) -> bool:
        ...

class MockPostRepository:
    def __init__(self):
        self.posts: List[Post] = []
        self._generate_mock_data()
    
    def _generate_mock_data(self):
        users = [
            User(id="1", name="John Doe", username="johndoe", avatar_url="https://example.com/avatar1.jpg"),
            User(id="2", name="Jane Smith", username="janesmith", avatar_url="https://example.com/avatar2.jpg"),
            User(id="3", name="Bob Johnson", username="bobjohnson", avatar_url="https://example.com/avatar3.jpg"),
        ]
        
        for i in range(1, 21):
            user = random.choice(users)
            post_type = random.choice(list(PostType))
            content = f"This is a sample post #{i} with some content."
            media_url = None
            
            if post_type == PostType.IMAGE:
                content = f"Check out this image post #{i}"
                media_url = "https://example.com/image.jpg"
            elif post_type == PostType.VIDEO:
                content = f"Video post #{i} - watch this!"
                media_url = "https://example.com/video.mp4"
            
            self.posts.append(
                Post(
                    id=str(i),
                    user=user,
                    content=content,
                    type=post_type,
                    likes=random.randint(0, 100),
                    comments=random.randint(0, 50),
                    shares=random.randint(0, 30),
                    timestamp=datetime.datetime.now() - datetime.timedelta(hours=random.randint(0, 72)),
                    media_url=media_url
                )
            )
    
    def fetch_posts(self, limit: int, offset: int) -> List[Post]:
        return sorted(self.posts[offset:offset+limit], key=lambda p: p.timestamp, reverse=True)
    
    def like_post(self, post_id: str) -> bool:
        for post in self.posts:
            if post.id == post_id:
                post.likes += 1
                post.liked = True
                return True
        return False
    
    def add_post(self, post: Post) -> bool:
        self.posts.insert(0, post)
        return True

# ----------------------------------
# ViewModel Layer
# ----------------------------------

class Observer(ABC):
    @abstractmethod
    def update(self, *args, **kwargs):
        pass

class Observable:
    def __init__(self):
        self._observers: List[Observer] = []
    
    def add_observer(self, observer: Observer):
        if observer not in self._observers:
            self._observers.append(observer)
    
    def remove_observer(self, observer: Observer):
        if observer in self._observers:
            self._observers.remove(observer)
    
    def notify_observers(self, *args, **kwargs):
        for observer in self._observers:
            observer.update(*args, **kwargs)

class FeedViewModel(Observable):
    def __init__(self, repository: PostRepositoryProtocol):
        super().__init__()
        self.repository = repository
        self.posts: List[Post] = []
        self.is_loading = False
        self.error: Optional[str] = None
        self.current_page = 0
        self.page_size = 10
        self.has_more = True
    
    def load_initial_posts(self):
        self.is_loading = True
        self.error = None
        self.notify_observers()
        
        try:
            new_posts = self.repository.fetch_posts(limit=self.page_size, offset=0)
            self.posts = new_posts
            self.current_page = 1
            self.has_more = len(new_posts) == self.page_size
        except Exception as e:
            self.error = str(e)
        finally:
            self.is_loading = False
            self.notify_observers()
    
    def load_more_posts(self):
        if not self.has_more or self.is_loading:
            return
        
        self.is_loading = True
        self.notify_observers()
        
        try:
            new_posts = self.repository.fetch_posts(
                limit=self.page_size, 
                offset=self.current_page * self.page_size
            )
            self.posts.extend(new_posts)
            self.current_page += 1
            self.has_more = len(new_posts) == self.page_size
        except Exception as e:
            self.error = str(e)
        finally:
            self.is_loading = False
            self.notify_observers()
    
    def refresh_posts(self):
        self.current_page = 0
        self.has_more = True
        self.load_initial_posts()
    
    def like_post(self, post_id: str):
        success = self.repository.like_post(post_id)
        if success:
            for post in self.posts:
                if post.id == post_id:
                    post.likes += 1
                    post.liked = True
                    break
            self.notify_observers()
    
    def create_post(self, content: str, post_type: PostType, media_url: Optional[str] = None):
        # In a real app, you'd get the current user from a user service
        user = User(id="current_user", name="Current User", username="currentuser")
        new_post = Post(
            id=str(len(self.posts) + 1),
            user=user,
            content=content,
            type=post_type,
            media_url=media_url
        )
        
        success = self.repository.add_post(new_post)
        if success:
            self.posts.insert(0, new_post)
            self.notify_observers()
            return True
        return False

# ----------------------------------
# View Layer (simplified for console demonstration)
# ----------------------------------

class FeedView(Observer):
    def __init__(self, view_model: FeedViewModel):
        self.view_model = view_model
        self.view_model.add_observer(self)
    
    def update(self, *args, **kwargs):
        self.render()
    
    def render(self):
        print("\n" + "="*50)
        print("SOCIAL MEDIA FEED")
        print("="*50)
        
        if self.view_model.error:
            print(f"\nError: {self.view_model.error}\n")
        
        if not self.view_model.posts and self.view_model.is_loading:
            print("\nLoading posts...\n")
            return
        
        for post in self.view_model.posts:
            self._render_post(post)
        
        if self.view_model.is_loading and self.view_model.posts:
            print("\nLoading more posts...\n")
        elif self.view_model.has_more:
            print("\nScroll to load more...\n")
        else:
            print("\nNo more posts to load.\n")
    
    def _render_post(self, post: Post):
        print("\n" + "-"*50)
        print(f"{post.user.name} (@{post.user.username})")
        print(f"Posted at: {post.timestamp.strftime('%Y-%m-%d %H:%M')}")
        print("\n" + post.content)
        
        if post.type == PostType.IMAGE:
            print(f"\n[IMAGE: {post.media_url}]")
        elif post.type == PostType.VIDEO:
            print(f"\n[VIDEO: {post.media_url}]")
        
        like_status = "♥" if post.liked else "♡"
        print(f"\n{like_status} {post.likes} likes | 💬 {post.comments} comments | ↪ {post.shares} shares")
        print("-"*50)

# ----------------------------------
# Plugin System for Custom Feed Items
# ----------------------------------

class FeedItemPlugin(ABC):
    @abstractmethod
    def can_handle(self, post: Post) -> bool:
        pass
    
    @abstractmethod
    def render(self, post: Post):
        pass

class ImagePostPlugin(FeedItemPlugin):
    def can_handle(self, post: Post) -> bool:
        return post.type == PostType.IMAGE
    
    def render(self, post: Post):
        print(f"\n[IMAGE CONTENT: {post.media_url}]\n{post.content}")

class VideoPostPlugin(FeedItemPlugin):
    def can_handle(self, post: Post) -> bool:
        return post.type == PostType.VIDEO
    
    def render(self, post: Post):
        print(f"\n[VIDEO PREVIEW: {post.media_url}]\n{post.content}")

class PluginFeedView(FeedView):
    def __init__(self, view_model: FeedViewModel, plugins: List[FeedItemPlugin]):
        super().__init__(view_model)
        self.plugins = plugins
    
    def _render_post(self, post: Post):
        for plugin in self.plugins:
            if plugin.can_handle(post):
                plugin.render(post)
                return
        
        # Default rendering if no plugin handles this post type
        super()._render_post(post)

# ----------------------------------
# Application Setup and Usage
# ----------------------------------

def main():
    # Setup dependencies
    repository = MockPostRepository()
    view_model = FeedViewModel(repository)
    
    # Create view with plugins
    plugins = [ImagePostPlugin(), VideoPostPlugin()]
    view = PluginFeedView(view_model, plugins)
    
    # Simulate user interaction
    view_model.load_initial_posts()
    
    # In a real app, this would be handled by user interaction
    # For demo purposes, we'll simulate some actions
    print("\nSimulating user actions...")
    
    # Like a post
    if view_model.posts:
        post_to_like = view_model.posts[0].id
        print(f"\nLiking post {post_to_like}")
        view_model.like_post(post_to_like)
    
    # Create a new post
    print("\nCreating a new text post...")
    view_model.create_post(
        content="This is a new post created through the app!",
        post_type=PostType.TEXT
    )
    
    # Create a new image post
    print("\nCreating a new image post...")
    view_model.create_post(
        content="Check out this beautiful sunset!",
        post_type=PostType.IMAGE,
        media_url="https://example.com/sunset.jpg"
    )
    
    # Refresh feed
    print("\nRefreshing feed...")
    view_model.refresh_posts()
    
    # Load more posts
    print("\nLoading more posts...")
    view_model.load_more_posts()

if __name__ == "__main__":
    main()