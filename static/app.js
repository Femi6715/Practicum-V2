const API_BASE_URL = '/.netlify/functions/api';

async function searchStudent() {
    const studentId = document.getElementById('studentId').value;
    if (!studentId) {
        alert('Please enter a student ID');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/student/${studentId}`);
        const data = await response.json();

        if (response.ok) {
            displayStudentInfo(data.student_info);
            displayCourses(data.courses);
            document.getElementById('studentInfo').style.display = 'block';
        } else {
            alert(data.error || 'Student not found');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while fetching student information');
    }
}

function displayStudentInfo(student) {
    const studentDetails = document.getElementById('studentDetails');
    studentDetails.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <div class="student-info-item">
                    <span class="student-info-label">Name:</span>
                    <span>${student.extracted_name || 'N/A'}</span>
                </div>
                <div class="student-info-item">
                    <span class="student-info-label">Email:</span>
                    <span>${student.email || 'N/A'}</span>
                </div>
                <div class="student-info-item">
                    <span class="student-info-label">Phone:</span>
                    <span>${student.phone || 'N/A'}</span>
                </div>
            </div>
            <div class="col-md-6">
                <div class="student-info-item">
                    <span class="student-info-label">Status:</span>
                    <span>${student.student_status || 'N/A'}</span>
                </div>
                <div class="student-info-item">
                    <span class="student-info-label">Field of Study:</span>
                    <span>${student.field_of_study || 'N/A'}</span>
                </div>
                <div class="student-info-item">
                    <span class="student-info-label">Program Format:</span>
                    <span>${student.program_format || 'N/A'}</span>
                </div>
            </div>
        </div>
    `;
}

function displayCourses(courses) {
    const coursesList = document.getElementById('coursesList');
    if (!courses || courses.length === 0) {
        coursesList.innerHTML = '<p>No courses found</p>';
        return;
    }

    const table = `
        <table class="table">
            <thead>
                <tr>
                    <th>Course Name</th>
                    <th>Credits</th>
                    <th>Grade</th>
                </tr>
            </thead>
            <tbody>
                ${courses.map(course => `
                    <tr class="course-row">
                        <td>${course.course_name}</td>
                        <td>${course.credits}</td>
                        <td>${course.grade}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    coursesList.innerHTML = table;
} 