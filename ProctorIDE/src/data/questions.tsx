export const questions = [
  {
    "id": 1,
    "title": "Two Sum",
    "difficulty": "Easy",
    "description": "Given an array of integers nums and an integer target, return the indices of the two numbers such that they add up to target.",
    "inputExample": {
      "nums": [2, 7, 11, 15],
      "target": 9
    },
    "outputExample": [0, 1],
    "constraints": [
      "2 <= nums.length <= 10^4",
      "-10^9 <= nums[i] <= 10^9",
      "Only one valid answer exists."
    ]
  },
  {
    "id": 2,
    "title": "Valid Palindrome",
    "difficulty": "Easy",
    "description": "Given a string s, determine if it is a palindrome, considering only alphanumeric characters and ignoring cases.",
    "inputExample": {
      "s": "A man, a plan, a canal: Panama"
    },
    "outputExample": true,
    "constraints": [
      "1 <= s.length <= 2 * 10^5",
      "s consists only of printable ASCII characters."
    ]
  },
  {
    "id": 3,
    "title": "Maximum Subarray",
    "difficulty": "Medium",
    "description": "Given an integer array nums, find the contiguous subarray which has the largest sum and return its sum.",
    "inputExample": {
      "nums": [-2,1,-3,4,-1,2,1,-5,4]
    },
    "outputExample": 6,
    "constraints": [
      "1 <= nums.length <= 10^5",
      "-10^4 <= nums[i] <= 10^4"
    ]
  },
  {
    "id": 4,
    "title": "Reverse Linked List",
    "difficulty": "Medium",
    "description": "Given the head of a singly linked list, reverse the list and return the reversed list.",
    "inputExample": {
      "head": [1, 2, 3, 4, 5]
    },
    "outputExample": [5, 4, 3, 2, 1],
    "constraints": [
      "The number of nodes in the list is in the range [0, 5000].",
      "-5000 <= Node.val <= 5000"
    ]
  }
]