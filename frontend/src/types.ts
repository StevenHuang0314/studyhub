export interface UserSummary {
  id: number
  username: string
}

export interface User extends UserSummary {
  email: string
  bio: string
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Note {
  id: number
  title: string
  content: string
  course_code: string
  tags: string[]
  resource_url: string
  author: UserSummary
  created_at: string
  updated_at: string
  average_rating: number | null
  rating_count: number
}

export interface Rating {
  id: number
  note_id: number
  score: number
  comment: string
  user: UserSummary
  created_at: string
  updated_at: string
}

export interface Member extends UserSummary {
  joined_at: string
}

export interface Group {
  id: number
  name: string
  description: string
  course_code: string
  meeting_time: string
  location: string
  capacity: number
  owner: UserSummary
  created_at: string
  updated_at: string
  member_count: number
  is_full: boolean
  members: Member[]
}

export interface Paginated<T> {
  items: T[]
  total: number
  skip: number
  limit: number
}

export type NoteSort = 'newest' | 'oldest' | 'top_rated' | 'most_rated'
