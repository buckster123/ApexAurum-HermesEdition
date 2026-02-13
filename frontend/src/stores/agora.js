import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useAgoraStore = defineStore('agora', () => {
  // State
  const posts = ref([])
  const loading = ref(false)
  const nextCursor = ref(null)
  const hasMore = ref(true)
  const activeFilter = ref(null)
  const selectedPost = ref(null)
  const settings = ref({
    enabled: false,
    auto_post_categories: {
      music_creation: true,
      council_insight: false,
      training_milestone: true,
      tool_showcase: false,
    },
    display_name_public: true,
  })

  // Actions
  async function fetchFeed(reset = false) {
    try {
      loading.value = true
      if (reset) {
        posts.value = []
        nextCursor.value = null
        hasMore.value = true
      }

      const params = {}
      if (nextCursor.value) params.cursor = nextCursor.value
      if (activeFilter.value) params.content_type = activeFilter.value

      const response = await api.get('/api/v1/agora/feed', { params })
      const data = response.data

      if (reset) {
        posts.value = data.posts || []
      } else {
        posts.value = [...posts.value, ...(data.posts || [])]
      }

      nextCursor.value = data.next_cursor || null
      hasMore.value = !!data.next_cursor
    } catch (e) {
      console.error('Failed to fetch Agora feed:', e)
      if (e.response?.status === 404) {
        // Agora not available yet - keep empty
        posts.value = []
        hasMore.value = false
      }
    } finally {
      loading.value = false
    }
  }

  async function loadMore() {
    if (!hasMore.value || loading.value) return
    await fetchFeed(false)
  }

  async function fetchPost(id) {
    try {
      loading.value = true
      const response = await api.get(`/api/v1/agora/posts/${id}`)
      selectedPost.value = response.data
      return response.data
    } catch (e) {
      console.error('Failed to fetch post:', e)
      selectedPost.value = null
      return null
    } finally {
      loading.value = false
    }
  }

  async function createPost(data) {
    try {
      loading.value = true
      const response = await api.post('/api/v1/agora/posts', data)
      // Prepend new post to feed
      posts.value = [response.data, ...posts.value]
      return response.data
    } catch (e) {
      console.error('Failed to create post:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function reactToPost(postId, reactionType) {
    // Optimistic update
    const post = posts.value.find(p => p.id === postId)
    if (!post) return

    const hadReaction = post.my_reactions?.includes(reactionType)

    // Toggle reaction locally
    if (hadReaction) {
      post.my_reactions = (post.my_reactions || []).filter(r => r !== reactionType)
      if (post.reactions && post.reactions[reactionType] > 0) {
        post.reactions[reactionType]--
      }
    } else {
      post.my_reactions = [...(post.my_reactions || []), reactionType]
      if (!post.reactions) post.reactions = {}
      post.reactions[reactionType] = (post.reactions[reactionType] || 0) + 1
    }

    try {
      await api.post(`/api/v1/agora/posts/${postId}/react`, {
        reaction_type: reactionType,
      })
    } catch (e) {
      console.error('Failed to react to post:', e)
      // Revert optimistic update
      if (hadReaction) {
        post.my_reactions = [...(post.my_reactions || []), reactionType]
        if (!post.reactions) post.reactions = {}
        post.reactions[reactionType] = (post.reactions[reactionType] || 0) + 1
      } else {
        post.my_reactions = (post.my_reactions || []).filter(r => r !== reactionType)
        if (post.reactions && post.reactions[reactionType] > 0) {
          post.reactions[reactionType]--
        }
      }
    }
  }

  async function addComment(postId, body, parentId = null) {
    try {
      const payload = { body }
      if (parentId) payload.parent_id = parentId

      const response = await api.post(`/api/v1/agora/posts/${postId}/comments`, payload)

      // Update local post comment count
      const post = posts.value.find(p => p.id === postId)
      if (post) {
        post.comment_count = (post.comment_count || 0) + 1
        if (!post.comments) post.comments = []
        post.comments.push(response.data)
      }

      return response.data
    } catch (e) {
      console.error('Failed to add comment:', e)
      throw e
    }
  }

  const leaderboard = ref([])
  const userRank = ref(null)
  const leaderboardLoading = ref(false)

  async function fetchLeaderboard() {
    try {
      leaderboardLoading.value = true
      const response = await api.get('/api/v1/agora/leaderboard')
      leaderboard.value = response.data.leaderboard || []
      userRank.value = response.data.user_rank
    } catch (e) {
      console.error('Failed to fetch leaderboard:', e)
      leaderboard.value = []
    } finally {
      leaderboardLoading.value = false
    }
  }

  async function flagPost(postId) {
    try {
      await api.post(`/api/v1/agora/posts/${postId}/flag`)
    } catch (e) {
      console.error('Failed to flag post:', e)
      throw e
    }
  }

  async function deletePost(postId) {
    try {
      await api.delete(`/api/v1/agora/posts/${postId}`)
      posts.value = posts.value.filter(p => p.id !== postId)
    } catch (e) {
      console.error('Failed to delete post:', e)
      throw e
    }
  }

  async function fetchSettings() {
    try {
      const response = await api.get('/api/v1/agora/settings')
      settings.value = response.data
    } catch (e) {
      if (e.response?.status === 404 || e.response?.status === 401) {
        // Keep defaults
      } else {
        console.error('Failed to fetch Agora settings:', e)
      }
    }
  }

  async function updateSettings(data) {
    try {
      const response = await api.put('/api/v1/agora/settings', data)
      settings.value = response.data
      return response.data
    } catch (e) {
      console.error('Failed to update Agora settings:', e)
      throw e
    }
  }

  return {
    // State
    posts,
    loading,
    nextCursor,
    hasMore,
    activeFilter,
    selectedPost,
    settings,
    leaderboard,
    userRank,
    leaderboardLoading,
    // Actions
    fetchFeed,
    loadMore,
    fetchPost,
    createPost,
    reactToPost,
    addComment,
    flagPost,
    deletePost,
    fetchSettings,
    updateSettings,
    fetchLeaderboard,
  }
})
