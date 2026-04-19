import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.menu_model import add_menu_item

items = [
    ("Trà Sữa Trân Châu Đen", 35000, 45000, "Trà sữa thơm béo với trân châu đen dai ngon"),
    ("Trà Sữa Trân Châu Trắng", 35000, 45000, "Trà sữa mịn với trân châu trắng thơm"),
    ("Trà Sữa Truyền Thống", 30000, 40000, "Trà sữa nguyên chất không topping"),
    ("Trà Sữa Khoai Môn", 38000, 48000, "Trà sữa vị khoai môn hấp dẫn"),
    ("Trà Sữa Bạc Hà", 35000, 45000, "Trà sữa thơm mát bạc hà tươi"),
    ("Trà Dâu Tây", 32000, 42000, "Trà tươi với vị dâu tây ngọt ngào"),
    ("Trà Mâm Xôi", 32000, 42000, "Trà mâm xôi tươi mát giải khát"),
    ("Trà Chanh Leo", 30000, 40000, "Trà chanh leo chua nhẹ sảng khoái"),
    ("Trà Vải Thiều", 33000, 43000, "Trà vải thiều ngọt hương lạ"),
    ("Trà Xoài", 32000, 42000, "Trà xoài tươi thơm vị nhiệt đới"),
    ("Cà Phê Đen", 25000, 30000, "Cà phê đen đậm đà truyền thống"),
    ("Cà Phê Sữa", 28000, 33000, "Cà phê sữa béo ngậy hạnh phúc"),
    ("Cà Phê Caramel", 30000, 35000, "Cà phê với ít caramel mượt mà"),
    ("Cà Phê Mocha", 32000, 37000, "Cà phê với chocolate ngọt dịu"),
    ("Cà Phê Macchiato", 27000, 32000, "Cà phê espresso với ít sữa"),
    ("Đá Xay Dâu Tây", 35000, 45000, "Đá xay mịn vị dâu tây tươi mát"),
    ("Đá Xay Dừa", 35000, 45000, "Đá xay vị dừa ngọt dễ chịu"),
    ("Đá Xay Matcha", 38000, 48000, "Đá xay matcha tươi giải khát"),
    ("Đá Xay Sôcôla", 36000, 46000, "Đá xay sôcôla ngọt thơm"),
    ("Trân Châu Đen", 5000, 5000, "Trân châu đen dai ngon"),
    ("Trân Châu Trắng", 5000, 5000, "Trân châu trắng mềm dẻo"),
    ("Thạch Cà Chua", 4000, 4000, "Thạch cà chua mọng nước"),
    ("Thạch Xanh", 4000, 4000, "Thạch xanh mát lạnh tươi"),
    ("Nước Cốt Dừa", 6000, 6000, "Nước cốt dừa béo ngậy"),
    ("Kem Tươi", 8000, 8000, "Kem tươi mịn ngọt dịu"),
    ("Gelée Khoai Môn", 5000, 5000, "Gelée khoai môn vị độc đáo"),
    ("Bột Trà Xanh", 3000, 3000, "Bột trà xanh thơm ngậy")
]

def seed():
    for item in items:
        add_menu_item(item[0], item[1], item[2], item[3])
    print("Database seeded completely!")

if __name__ == "__main__":
    seed()
