from sympy import symbols, Eq, solve, simplify, latex
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
import matplotlib.pyplot as plt
import numpy as np
import io

# تبدیل‌های پیشرفته برای تجزیه عبارات ریاضی
transformations = (standard_transformations + (implicit_multiplication_application,))

# تابع برای تبدیل ^ به **
def convert_power_symbol(formula):
    return formula.replace('^', '**')

# تابع برای ایجاد تصویر از متن با استفاده از matplotlib
def create_image_from_text(text):
    # تنظیم حالت غیرتعاملی برای matplotlib
    plt.switch_backend('Agg')

    # ایجاد یک شکل جدید
    fig, ax = plt.subplots(figsize=(10, 2))
    ax.text(0.1, 0.5, text, fontsize=14, va='center', ha='left')
    ax.axis('off')  # غیرفعال کردن محورها

    # ذخیره تصویر در یک بافر
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1)
    buf.seek(0)
    plt.close()
    return buf

# تابع برای رسم نمودار معادلات چندجمله‌ای
def plot_polynomial(expr, var):
    # تنظیم حالت غیرتعاملی برای matplotlib
    plt.switch_backend('Agg')

    # ایجاد یک شکل جدید
    fig, ax = plt.subplots(figsize=(8, 6))

    # محدوده مقادیر متغیر
    x_vals = np.linspace(-2, 2, 400)
    y_vals = [expr.subs(var, x_val) for x_val in x_vals]

    # رسم نمودار
    ax.plot(x_vals, y_vals, label=f'{expr}')
    ax.axhline(0, color='black', linewidth=0.5)
    ax.axvline(0, color='black', linewidth=0.5)
    ax.set_xlabel(str(var))
    ax.set_ylabel("y")
    ax.legend()
    ax.grid(True)

    # ذخیره نمودار در یک بافر
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

# تابع برای حل معادلات و رسم نمودار
def calculate_and_plot(formula):
    try:
        # تبدیل ^ به **
        formula = convert_power_symbol(formula)

        # تشخیص نوع معادله
        if '=' in formula:
            # معادله با یک یا چند متغیر
            lhs, rhs = formula.split('=')
            x = symbols('x')
            lhs_expr = parse_expr(lhs, transformations=transformations)
            rhs_expr = parse_expr(rhs, transformations=transformations)
            equation = Eq(lhs_expr, rhs_expr)

            # حل معادله
            solution = solve(equation, x)

            # آماده‌سازی پاسخ
            response = r"$\text{راه‌حل معادله:}$" + "\n"
            for sol in solution:
                sol_str = latex(sol)  # تبدیل جواب به فرمت LaTeX
                response += f"$x = {sol_str}$\n"

            # رسم نمودار برای معادلات چندجمله‌ای
            plot_buf = plot_polynomial(lhs_expr - rhs_expr, x)
            return response, plot_buf
        else:
            # محاسبه ساده
            result = simplify(parse_expr(formula, transformations=transformations))
            result_str = latex(result)  # تبدیل نتیجه به فرمت LaTeX
            response = r"$\text{نتیجه:}$" + f" ${result_str}$"

            # ارسال پاسخ به صورت عکس
            image_buf = create_image_from_text(response)
            return response, image_buf

    except Exception as e:
        error_message = f"خطا: {str(e)}"
        image_buf = create_image_from_text(error_message)
        return error_message, image_buf
